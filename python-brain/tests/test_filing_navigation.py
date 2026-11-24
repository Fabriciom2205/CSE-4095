"""Offline checks for archived submissions, linked sections, and risk-factor diffs."""

import unittest
from unittest.mock import Mock, patch

import filing_sections
import sec_client

CIK = "0000320193"
CURRENT = "0000320193-25-000079"
PREVIOUS = "0000320193-24-000123"


def batch(*rows):
    return dict(zip(("form", "filingDate", "accessionNumber", "primaryDocument", "reportDate"),
                    zip(*rows, strict=True), strict=True))


def html(risk):
    return f"""
    <table><tr><td><a href="#risks">Item 1A.</a></td><td>Risk Factors</td></tr>
    <tr><td><a href="#next">Item 1B.</a></td></tr></table>
    <div id="risks"></div><h2>Item 1A. Risk Factors</h2>
    <p>{risk}</p><p hidden>Hidden data</p>
    <div id="next"><h2>Item 1B. Unresolved Staff Comments</h2></div><p>Outside the section</p>
    """


class FilingNavigationTests(unittest.TestCase):
    def test_timeline_filters_archives_and_links_ownership_xml(self):
        recent = batch(("4", "2025-11-04", CURRENT, "xslF345X05/form4.xml", "2025-11-03"))
        archive = batch(("DEF 14A", "2024-10-31", PREVIOUS, "proxy.htm", ""))
        index = {"filings": {"recent": recent, "files": [
            {"name": "old.json", "filingTo": "2023-12-31"},
            {"name": "prior.json", "filingTo": "2024-12-31"},
        ]}}
        with patch.object(sec_client, "_rate_limited_get", side_effect=[Mock(**{"json.return_value": index}),
                                                                      Mock(**{"json.return_value": archive})]) as get:
            result = sec_client.filing_timeline("320193", "def 14a", "2024-01-01")
        self.assertEqual(get.call_count, 2)
        self.assertTrue(get.call_args.args[0].endswith("/prior.json"))
        self.assertEqual(result["filings"][0]["url"],
                         "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/proxy.htm")
        with patch.object(sec_client, "_submission_batches", return_value=iter([recent, archive])):
            result = sec_client.filing_timeline(CIK, limit=1)
        self.assertTrue(result["truncated"])
        self.assertTrue(result["filings"][0]["url"].endswith("/xslF345X05/form4.xml"))

    def test_annual_diff_uses_body_anchors_and_keeps_citations(self):
        filings = [{"accession_number": CURRENT, "filename": "current.htm", "report_date": "2025-09-27"},
                   {"accession_number": PREVIOUS, "filename": "previous.htm", "report_date": "2024-09-28"}]
        with patch.object(sec_client, "filing_timeline", return_value={"filings": filings}), \
             patch.object(sec_client, "tool_fetch_filing_text", side_effect=[html("A minor risk."), html("A material risk.")]):
            result = filing_sections.risk_factor_diff(CIK)
        self.assertIn("-A minor risk.", result["diff"])
        self.assertIn("+A material risk.", result["diff"])
        self.assertNotIn("Hidden", result["diff"])
        self.assertNotIn("Outside", result["diff"])
        self.assertEqual(result["older"]["accession_number"], PREVIOUS)
        self.assertEqual(result["newer"]["accession_number"], CURRENT)

    def test_quarterly_part_stops_at_next_part_and_missing_link_is_explicit(self):
        document = ('<a href="#i">Part I</a><a href="#ii">Part II</a>'
                    '<div id="i">PART I</div><p>Statements</p>'
                    '<div id="ii">PART II</div><p>Litigation</p>')
        with patch.object(sec_client, "tool_fetch_filing_text", return_value=document):
            result = filing_sections.filing_section(CIK, CURRENT, "quarter.htm", "10-Q", "Part I")
        self.assertIn("Statements", result["text"])
        self.assertNotIn("Litigation", result["text"])
        with self.assertRaisesRegex(ValueError, "unique linked heading"):
            filing_sections._section_blocks("<h2>Item 1A. Risk Factors</h2>", "item 1a")

    def test_descriptive_fragments_supply_missing_numbers(self):
        html = ('<a href="#part_ii_other_information">OTHER INFORMATION</a>'
                '<a href="#item_1a_risk_factors">Risk Factors</a>'
                '<a href="#item2_sales">Sales</a><a href="#signature">SIGNATURES</a>'
                '<div id="part_ii_other_information">Part II</div>'
                '<h2 id="item_1a_risk_factors">Risk Factors</h2><p>Contingencies</p>'
                '<h2 id="item2_sales">Sales</h2><p>Unregistered sales</p>'
                '<div id="signature">Signed</div>')
        self.assertEqual(filing_sections._section_blocks(html, "item 1a"), ["Risk Factors", "Contingencies"])
        self.assertNotIn("Signed", filing_sections._section_blocks(html, "part ii"))


if __name__ == "__main__":
    unittest.main()
