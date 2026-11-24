"""Regression checks for sourced insider transactions and institutional holdings."""

from copy import deepcopy
import unittest
from unittest.mock import patch

import adk_runtime
import figure_sources as figures
import mcp_server
import sec_client


def filing(accession, form, period, filed, filename="xslForm13F_X02/primary_doc.xml"):
    return {"accession_number": accession, "form": form, "report_date": period, "filing_date": filed,
            "filename": filename, "url": f"https://www.sec.gov/{accession}"}


def ownership(owner_cik="0001043298"):
    return f"""<ownershipDocument>
<issuer><issuerName>Example Inc.</issuerName><issuerTradingSymbol>EX</issuerTradingSymbol></issuer>
<reportingOwner><reportingOwnerId><rptOwnerCik>{owner_cik}</rptOwnerCik>
<rptOwnerName>Bezos</rptOwnerName></reportingOwnerId></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction>
<transactionDate><value>2026-01-02</value></transactionDate>
<securityTitle><value>Common Stock</value></securityTitle>
<transactionCoding><transactionCode>G</transactionCode></transactionCoding>
<transactionAmounts><transactionShares><value>4.5</value></transactionShares>
<transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts>
</nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""


class FigureSourceTests(unittest.TestCase):
    def test_form4_keeps_gift_distinct_from_sale_and_preserves_source_dates(self):
        row = filing("0001043298-26-000002", "4", "2026-01-02", "2026-01-05", "xslF345X06/report.xml")
        with patch.object(figures, "_filings", return_value=([row], False)), \
             patch.object(sec_client, "tool_fetch_filing_text", return_value=ownership()) as fetch:
            result = figures.lookup("Jeff Bezos", "form4")
        self.assertEqual(result["cik"], "0001043298")
        transaction = result["transactions"][0]
        self.assertEqual(transaction["transaction_type"], "gift")
        self.assertEqual(transaction["disposition"], "D")
        self.assertEqual(transaction["shares"], "4.5")
        self.assertIsNone(transaction["price_per_share"])
        self.assertEqual(transaction["transaction_date"], "2026-01-02")
        self.assertEqual(transaction["source"]["filing_date"], "2026-01-05")
        fetch.assert_called_once_with("0001043298", row["accession_number"], "report.xml")

    def test_form4_discards_reports_by_a_different_owner(self):
        row = filing("0001043298-26-000002", "4", "2026-01-02", "2026-01-05", "report.xml")
        with patch.object(figures, "_filings", return_value=([row], False)), \
             patch.object(sec_client, "tool_fetch_filing_text", return_value=ownership("999")):
            self.assertEqual(figures.lookup("Jeff Bezos", "form4")["transactions"], [])

    def test_13f_keeps_classes_separate_and_uses_restatement_then_additions(self):
        previous = filing("0001193125-26-000001", "13F-HR", "2026-06-30", "2026-08-12")
        current = filing("0001193125-26-000002", "13F-HR", "2026-09-30", "2026-11-10")
        amended = filing("0001193125-26-000003", "13F-HR/A", "2026-09-30", "2026-11-12")
        added = filing("0001193125-26-000004", "13F-HR/A", "2026-09-30", "2026-11-14")
        key = ("000000001", "COM", "SH", None)
        call = ("000000001", "COM", "SH", "Call")
        tables = {
            previous["accession_number"]: {key: ("EX", 10, 100), call: ("EX", 2, 20)},
            current["accession_number"]: {key: ("EX", 1000, 1000)},
            amended["accession_number"]: {key: ("EX", 15, 150), call: ("EX", 2, 20)},
            added["accession_number"]: {key: ("EX", 3, 30)},
        }
        def amendment(_, row, *args):
            kind = "RESTATEMENT" if row == amended else "NEW HOLDINGS"
            return figures.ET.fromstring(f"<edgarSubmission><formData><coverPage><amendmentInfo>"
                                         f"<amendmentType>{kind}</amendmentType></amendmentInfo>"
                                         "</coverPage></formData></edgarSubmission>")
        with patch.object(figures, "_filings", return_value=([added, amended, previous, current], False)), \
             patch.object(figures, "_positions", side_effect=lambda _, row: deepcopy(tables[row["accession_number"]])), \
             patch.object(figures, "_xml", side_effect=amendment):
            result = figures.lookup("Warren Buffett", "13f")
        self.assertEqual(result["filer"], "Berkshire Hathaway Inc.")
        self.assertEqual([r["accession_number"] for r in result["sources"]],
                         [amended["accession_number"], added["accession_number"], previous["accession_number"]])
        self.assertEqual(len(result["holdings_changes"]), 1)
        change = result["holdings_changes"][0]
        self.assertEqual((change["previous_amount"], change["current_amount"], change["change"]), (10, 18, "increased"))
        self.assertNotIn("transaction_date", change)

    def test_table_lookup_ignores_host_and_validates_sec_filename(self):
        row = filing("0001193125-26-000001", "13F-HR", "2026-06-30", "2026-08-12")
        index = """<table><tr><td>2</td><td>Holdings</td><td><a href="https://elsewhere.invalid/">60471.xml</a>
</td><td>INFORMATION TABLE</td></tr></table>"""
        with patch.object(sec_client, "tool_fetch_filing_text", return_value=index):
            self.assertEqual(figures._table_filename("1067983", row), "60471.xml")
        with patch.object(sec_client, "tool_fetch_filing_text", return_value="<!DOCTYPE bad><ownershipDocument/>"):
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                figures._xml("1067983", row, "report.xml", "ownershipDocument")

    def test_unknown_names_and_unbounded_results_are_rejected(self):
        with self.assertRaises(ValueError):
            figures.lookup("Nancy Pelosi", "form4")
        with self.assertRaises(ValueError):
            figures.lookup("Warren Buffett", "13f", 21)


class FigureAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_adk_adds_actual_accession_to_citation_collector(self):
        row = filing("0001193125-26-463399", "13F-HR", "2026-09-30", "2026-11-16")
        data = {"filer": "Berkshire Hathaway Inc.", "sources": [row]}
        sources = []
        token = adk_runtime._evidence.set(sources)
        try:
            with patch.object(mcp_server.figure_sources, "lookup", return_value=data):
                result = await adk_runtime.sec_figure_disclosures("Warren Buffett", "13f")
        finally:
            adk_runtime._evidence.reset(token)
        self.assertEqual(result["source"], "SEC EDGAR")
        self.assertEqual(sources[0].accession, row["accession_number"])
        self.assertEqual(sources[0].filer, data["filer"])
        self.assertIsNone(sources[0].symbol)
