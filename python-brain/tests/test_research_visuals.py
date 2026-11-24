"""Opt-in intent and data provenance for research visuals."""

import os
import unittest
from unittest.mock import patch

from research_visuals import requested_visual, statement_visual


class ResearchVisualTests(unittest.TestCase):
    def test_only_current_explicit_visual_requests_are_recognized(self):
        for question, expected in (
            ("Show Apple's revenue in a table.", "table"),
            ("Could you turn that into a table?", "table"),
            ("Give me a bar chart of revenue.", "bar"),
            ("Compare the amounts. Plot it.", "line"),
            ("What does the table in the 10-K show?", None),
            ("Summarize the filing without a chart.", None),
            ("Explain what the issuer reported in a table in the filing.", None),
        ):
            with self.subTest(question=question):
                self.assertEqual(requested_visual(question), expected)

    def test_statement_visual_preserves_exact_values_gaps_and_q4_provenance(self):
        accession = "0000320193-25-000079"
        nine_months = "0000320193-25-000073"
        data = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"start": "2024-09-29", "end": "2025-09-27", "val": 9007199254741093, "accn": accession,
             "filed": "2025-11-01", "form": "10-K"},
            {"start": "2024-09-29", "end": "2025-06-28", "val": 100, "accn": nine_months,
             "filed": "2025-08-01", "form": "10-Q"},
        ]}}}}}

        def timeline(cik, *, form, limit):
            return {"filings": [{"report_date": "2025-09-27" if form == "10-K" else "2025-06-28"}]}

        with patch.dict(os.environ, {"SEC_DB_READ_DSN": ""}), \
             patch("sec_client.resolve_cik", return_value="0000320193"), \
             patch("sec_client.filing_timeline", side_effect=timeline), \
             patch("sec_client.company_facts", return_value=data) as facts:
            visual = statement_visual("bar", "AAPL", "income_statement", ["revenue", "operating_income"],
                                      "quarter", 2, [], [], "USD").model_dump(mode="json")
        facts.assert_called_once()
        self.assertEqual([row["period"] for row in visual["rows"]], ["quarter", "q4"])
        q4 = visual["rows"][1]["cells"]
        self.assertEqual(q4["revenue"]["value"], "9007199254740993")
        self.assertTrue(q4["revenue"]["derived"])
        self.assertEqual(q4["revenue"]["period_start"], "2025-06-29")
        self.assertEqual([source["accession"] for source in q4["revenue"]["sources"]], [accession, nine_months])
        self.assertEqual(q4["revenue"]["sources"][1]["role"], "nine_months")
        self.assertIsNone(q4["operating_income"]["value"])
