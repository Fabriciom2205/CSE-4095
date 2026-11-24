"""Offline checks for Alpaca reads, normalization and credential boundaries."""

from decimal import Decimal
import os
import unittest
from unittest.mock import Mock, patch

import requests

import alpaca_client as alpaca


class AlpacaClientTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(
            os.environ,
            {"ALPACA_API_KEY_ID": "test-key", "ALPACA_API_SECRET_KEY": "test-secret"},
            clear=True,
        )
        self.addCleanup(environment.stop)
        environment.start()
        request = patch.object(alpaca._session, "get")
        self.addCleanup(request.stop)
        self.get = request.start()

    def response(self, data, status=200):
        self.get.return_value = Mock(status_code=status, **{"json.return_value": data})

    def test_account_uses_paper_and_decimals(self):
        self.response({"id": "account-id", "status": "ACTIVE", "currency": "USD", "equity": "1234.56",
                       "cash": "300.01", "buying_power": "550.05", "account_number": "not needed"})
        account = alpaca.get_account()
        self.assertEqual(account, {
            "provider": "alpaca", "environment": "paper", "external_account_id": "account-id",
            "status": "ACTIVE", "currency": "USD", "equity": Decimal("1234.56"), "cash": Decimal("300.01"),
            "buying_power": Decimal("550.05"),
        })
        self.get.assert_called_once_with(
            "https://paper-api.alpaca.markets/v2/account", params=None,
            headers={"APCA-API-KEY-ID": "test-key", "APCA-API-SECRET-KEY": "test-secret"},
            timeout=15, allow_redirects=False,
        )

    def test_positions_preserve_fractional_and_short_exposure(self):
        fields = {"asset_class": "us_equity", "market_value": "430.11", "cost_basis": "400.02",
                  "unrealized_pl": "30.09", "qty": "2.125"}
        self.response([dict(fields, asset_id="asset-1", symbol="AAA", side="long"),
                       dict(fields, asset_id="asset-2", symbol="BBB", side="short", qty="-1.25",
                            unrealized_pl="-30.09"),
                       dict(fields, asset_id="asset-3", symbol="CCC", side="long", market_value=None,
                            unrealized_pl=None)])
        first, second, third = alpaca.get_positions()
        self.assertEqual(first["quantity"], Decimal("2.125"))
        self.assertEqual(first["market_value"], Decimal("430.11"))
        self.assertEqual(first["cost_basis"], Decimal("400.02"))
        self.assertEqual(first["unrealized_pl"], Decimal("30.09"))
        self.assertEqual(second["quantity"], Decimal("-1.25"))
        self.assertEqual(second["market_value"], Decimal("-430.11"))
        self.assertEqual(second["unrealized_pl"], Decimal("-30.09"))
        self.assertIsNone(third["market_value"])
        self.assertIsNone(third["unrealized_pl"])
        self.assertTrue(self.get.call_args.args[0].endswith("/v2/positions"))

    def test_order_get_is_bounded_and_preserves_notional_order(self):
        self.response([{"id": "order", "symbol": "AAPL", "side": "buy", "type": "market",
                        "status": "partially_filled", "notional": "150", "filled_qty": "0.25",
                        "filled_avg_price": "200.25", "submitted_at": "2026-02-01T00:00:00Z"}])
        os.environ["ALPACA_BASE_URL"] = "https://api.alpaca.markets/"
        order, = alpaca.get_orders("open", 75)
        self.assertEqual(order["external_order_id"], "order")
        self.assertIsNone(order["quantity"])
        self.assertEqual(order["notional"], Decimal("150"))
        self.assertEqual(order["filled_quantity"], Decimal("0.25"))
        self.assertEqual(order["filled_avg_price"], Decimal("200.25"))
        self.assertEqual(self.get.call_args.args[0], "https://api.alpaca.markets/v2/orders")
        self.assertEqual(self.get.call_args.kwargs["params"], {"status": "open", "limit": 75, "direction": "desc"})
        for status, limit in (("filled", 1), ("all", 501), ("all", True)):
            with self.subTest(status=status, limit=limit), self.assertRaises(ValueError):
                alpaca.get_orders(status, limit)
        self.get.assert_called_once()

    def test_order_json_numbers_decode_directly_as_decimals(self):
        response = requests.Response()
        response.status_code = 200
        response._content = b'[{"id":"order","status":"new","filled_qty":0,"qty":0.1234567890123456789}]'
        self.get.return_value = response
        order, = alpaca.get_orders()
        self.assertEqual(order["quantity"], Decimal("0.1234567890123456789"))
        self.assertIsNone(order["type"])

    def test_invalid_base_urls_and_placeholder_credentials_do_not_send_requests(self):
        for url in ("http://paper-api.alpaca.markets", "https://api.alpaca.markets.example", "https://other@api.alpaca.markets"):
            os.environ["ALPACA_BASE_URL"] = url
            with self.subTest(url=url), self.assertRaisesRegex(alpaca.AlpacaError, "official HTTPS"):
                alpaca.get_account()
        del os.environ["ALPACA_BASE_URL"]
        os.environ["ALPACA_API_SECRET_KEY"] = "your_alpaca_secret_key_here"
        self.assertFalse(alpaca.credentials_configured())
        with self.assertRaisesRegex(alpaca.AlpacaError, "ALPACA_API_SECRET_KEY"):
            alpaca.get_account()
        self.get.assert_not_called()

    def test_upstream_errors_never_include_response_or_credentials(self):
        for status, message in ((302, "redirects"), (401, "HTTP 401"), (429, "HTTP 429"), (502, "HTTP 502")):
            with self.subTest(status=status):
                self.response({"secret": "test-secret"}, status)
                with self.assertRaisesRegex(alpaca.AlpacaError, message) as error:
                    alpaca.get_positions()
                self.assertNotIn("test-secret", str(error.exception))
                self.get.return_value.json.assert_not_called()
        self.get.side_effect = requests.Timeout("test-secret")
        with self.assertRaisesRegex(alpaca.AlpacaError, "^Alpaca request failed$") as error:
            alpaca.get_account()
        self.assertIsNone(error.exception.__cause__)

    def test_malformed_json_and_nonfinite_financial_values_fail_closed(self):
        self.get.return_value = Mock(status_code=200)
        self.get.return_value.json.side_effect = ValueError("upstream response content")
        with self.assertRaisesRegex(alpaca.AlpacaError, "^Alpaca returned invalid JSON$"):
            alpaca.get_account()
        self.response({"id": "account", "status": "ACTIVE", "equity": "NaN"})
        with self.assertRaisesRegex(alpaca.AlpacaError, "invalid equity"):
            alpaca.get_account()
        self.response({"not": "an array"})
        with self.assertRaisesRegex(alpaca.AlpacaError, "invalid collection"):
            alpaca.get_positions()
