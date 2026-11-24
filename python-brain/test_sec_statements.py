"""Regression tests for typed financial reads and source fallback."""

from datetime import date
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

import filing_store
import sec_client
import sec_statements


class StatementTests(unittest.TestCase):
    def test_q4_uses_latest_matching_context_and_keeps_both_accessions(self):
        def point(value, end, accession, filed, start=None):
            return {"start": start, "end": end, "val": value, "accn": accession,
                    "filed": filed, "form": "10-K/A" if accession == "amended" else "10-K"}

        annual = ("2025-12-31", "original", "2026-02-01", "2025-01-01")
        revenue = {"units": {
            "USD": [
                point(110, *annual),
                point(120, "2025-12-31", "amended", "2026-03-01", "2025-01-01"),
                point(90, "2025-09-30", "nine", "2025-11-01", "2025-01-01"),
                point(999, "2025-12-31", "tagged_q4", "2026-02-01", "2025-10-01"),
                point(999, "2025-12-31", "instant", "2026-03-01"),
            ],
            "USD/shares": [point(999, *annual)],
        }}
        data = {"facts": {"us-gaap": {"Revenues": revenue}}}
        with patch.dict(os.environ, {"SEC_DB_READ_DSN": "unused"}), \
             patch.object(filing_store, "query_facts", return_value=[]) as query, \
             patch.object(sec_client, "company_facts", return_value=data) as edgar:
            lines = sec_statements.company_statement("1", "income_statement", "2025-12-31", "q4", "USD")["lines"]
        self.assertFalse(query.call_args.kwargs["instant"])
        self.assertIn(("us-gaap", "Revenues", "USD"), query.call_args.args[2])
        edgar.assert_called_once()
        line = lines["revenue"]
        self.assertEqual(line["value"], "30")
        self.assertTrue(line["derived"])
        self.assertEqual(line["period_start"], "2025-10-01")
        self.assertEqual([source["accession"] for source in line["sources"]], ["amended", "nine"])
        self.assertEqual(lines["net_income"]["status"], "missing_or_ambiguous")

    def test_raw_facts_fall_back_on_database_failure(self):
        with patch.dict(os.environ, {"SEC_DB_READ_DSN": "unused"}), \
             patch.object(filing_store, "query_facts", side_effect=filing_store.FilingStoreError("offline")), \
             patch.object(sec_client, "tool_get_financial_facts", return_value={"label": "Assets"}) as edgar, \
             self.assertLogs("sec_statements", "WARNING"):
            self.assertEqual(sec_statements.get_financial_facts("1", "Assets"), {"label": "Assets"})
        edgar.assert_called_once_with("0000000001", "Assets")

    def test_same_day_conflicting_values_remain_unresolved(self):
        cutoff = date(2026, 1, 30)
        period = date(2025, 12, 31)
        rows = [("us-gaap", "Assets", "USD", None, period, Decimal(value), accession, cutoff, "10-K", False)
                for value, accession in [(10, "a"), (20, "b")]]
        with patch.object(sec_statements, "_read_facts", return_value=rows), \
             patch.object(sec_statements, "_edgar_rows", return_value=rows):
            lines = sec_statements.company_statement("1", "balance_sheet", "2025-12-31", "annual", "USD")["lines"]
        self.assertIsNone(lines["assets"]["value"])


if __name__ == "__main__":
    unittest.main()
