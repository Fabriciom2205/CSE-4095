"""Portfolio limits use the EDGAR industry classification."""

import unittest
from unittest.mock import patch

import portfolio_sectors


class SectorTests(unittest.TestCase):
    def tearDown(self):
        portfolio_sectors._sector.cache_clear()

    def test_reads_and_caches_classified_issuer_and_rejects_special_cases(self):
        with patch("sec_client.resolve_cik", return_value="0000000001"), \
             patch("sec_client.company_submissions", side_effect=[
                 {"cik": 1, "sic": "3674"}, {"cik": 1, "sic": "8880"}, {"cik": 2, "sic": "3674"},
             ]) as read:
            self.assertEqual(portfolio_sectors.classifications(["AAA", "AAA"]), {"AAA": "manufacturing"})
            portfolio_sectors.classifications(["AAA"])
            read.assert_called_once_with("0000000001")
            for symbol in ("ADR", "WRONG"):
                with self.assertRaisesRegex(ValueError, f"classification for {symbol}"):
                    portfolio_sectors.classifications([symbol])
