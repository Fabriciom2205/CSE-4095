"""Offline fixture for the SEC-to-PostgreSQL importer."""

from decimal import Decimal
import unittest
from unittest.mock import patch

import ingest_sec


class IngestTest(unittest.TestCase):
    def test_builds_filing_batch_without_losing_precision(self):
        accession = "0000320193-25-000001"
        point = {"val": Decimal("9007199254740993.01"), "accn": accession,
                 "end": "2024-12-31", "form": "10-K", "filed": "2025-02-01"}
        company = {"cik": 320193, "entityName": "Apple", "facts": {
            "us-gaap": {"Assets": {"units": {"USD": [point]}}}}}
        filing = {"accession_number": accession, "filing_date": "2025-02-01", "filename": "aapl.htm"}
        with (
            patch.object(ingest_sec.sec_client, "resolve_cik", return_value="0000320193"),
            patch.object(ingest_sec.sec_client, "company_facts", return_value=company),
            patch.object(ingest_sec.sec_client, "latest_10k", return_value=filing),
            patch.object(ingest_sec.sec_client, "tool_fetch_filing_text",
                         return_value='<ix:nonNumeric name="dei:AuditorName"> Example  LLP </ix:nonNumeric>'),
        ):
            batch = ingest_sec.company_batch("AAPL", ["us-gaap:Assets"], True)

        self.assertEqual(batch["facts"][0]["value"], "9007199254740993.01")
        self.assertIsNone(batch["facts"][0]["period_start"])
        self.assertEqual(batch["filings"][0], batch["filings"][1])
        self.assertEqual(batch["auditors"], [
            {"accession": accession, "key": "example llp", "label": "Example LLP"},
        ])


if __name__ == "__main__":
    unittest.main()
