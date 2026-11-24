"""Offline fixture for the SEC-to-PostgreSQL importer."""

from decimal import Decimal
import unittest
from unittest.mock import patch

import ingest_sec
from sec_dimensions import dimensions_from_instance


class IngestTest(unittest.TestCase):
    def test_dimensional_instance_keeps_full_axes_and_exact_period(self):
        instance = """<xbrl xmlns="http://www.xbrl.org/2003/instance"
            xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
            xmlns:us="http://fasb.org/us-gaap/2025" xmlns:srt="http://fasb.org/srt/2025"
            xmlns:issuer="https://issuer.example/2025" xmlns:iso="http://www.xbrl.org/2003/iso4217">
          <context id="segment">
            <entity><identifier scheme="http://www.sec.gov/CIK">0000320193</identifier><segment>
              <xbrldi:explicitMember dimension="us:StatementBusinessSegmentsAxis">issuer:HardwareMember</xbrldi:explicitMember>
              <xbrldi:explicitMember dimension="srt:StatementGeographicalAxis">issuer:EuropeMember</xbrldi:explicitMember>
            </segment></entity>
            <period><startDate>2024-10-01</startDate><endDate>2024-12-31</endDate></period>
          </context>
          <unit id="usd"><measure>iso:USD</measure></unit>
          <us:Revenues contextRef="segment" unitRef="usd">9007199254740993.01</us:Revenues>
          <us:Assets contextRef="segment" unitRef="usd">999</us:Assets>
          <us:Revenues contextRef="segment" unitRef="unknown">55</us:Revenues>
        </xbrl>"""
        rows = dimensions_from_instance(instance, "0000320193", "0000320193-25-000001")
        self.assertEqual([row["predicate"] for row in rows], ["revenue_segment", "revenue_geography"])
        self.assertEqual(rows[0]["value"], "9007199254740993.01")
        self.assertEqual((rows[0]["period_start"], rows[0]["period_end"], rows[0]["unit"]),
                         ("2024-10-01", "2024-12-31", "USD"))
        self.assertEqual(rows[0]["key"], rows[1]["key"])
        self.assertIn("{https://issuer.example/2025}EuropeMember", rows[0]["key"])
        self.assertIn("StatementBusinessSegmentsAxis=HardwareMember", rows[0]["label"])
        self.assertEqual(dimensions_from_instance(instance, "0000789019", "0000320193-25-000001"), [])

    def test_historical_auditors_keep_separate_filing_provenance(self):
        filings = [
            {"accession_number": "0000320193-25-000001", "filing_date": "2025-11-01", "filename": "b.htm"},
            {"accession_number": "0000320193-24-000001", "filing_date": "2024-11-01", "filename": "a.htm"},
            {"accession_number": "0000320193-23-000001", "filing_date": "2023-11-01", "filename": "older.htm"},
        ]
        with (patch.object(ingest_sec.sec_client, "resolve_cik", return_value="0000320193"),
              patch.object(ingest_sec.sec_client, "company_facts",
                           return_value={"cik": 320193, "entityName": "Apple", "facts": {}}),
              patch.object(ingest_sec.sec_client, "filing_timeline", return_value={"filings": filings}) as timeline,
              patch.object(ingest_sec.sec_client, "tool_fetch_filing_text", side_effect=[
                  '<ix:nonnumeric name="dei:AuditorName"><span>N</span><span>ew</span> LLP</ix:nonnumeric>',
                  '<ix:nonnumeric name="dei:AuditorName">Old LLP</ix:nonnumeric>',
                  "<p>Untagged audit report.</p>",
              ])):
            batch = ingest_sec.company_batch("AAPL", [], False, auditor_filings=3)
        timeline.assert_called_once_with("0000320193", form="10-K", limit=3)
        self.assertEqual([(row["accession"], row["label"]) for row in batch["auditors"]], [
            (filings[0]["accession_number"], "New LLP"), (filings[1]["accession_number"], "Old LLP"),
        ])

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
