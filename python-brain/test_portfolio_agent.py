"""Execution mode tests use a mocked broker. They never submit a real order."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from contextlib import nullcontext
import os
from uuid import uuid4
import unittest
from unittest.mock import Mock, patch

import alpaca_client
import portfolio_agent as runner
import portfolio_store
from propose import Proposal
from risk import RiskLimits

LIMITS = RiskLimits(max_name_weight=D(".5"), max_drawdown=D(".1"),
                    max_order_notional=D(300), max_gross_notional=D(900))


def proposal(symbol="NVDA", weight="0.2"):
    return Proposal.model_validate({"targets": [{
        "symbol": symbol, "target_weight": weight, "confidence": "0.5", "rationale": "Test fixture",
        "evidence": {"accessions": ["0001045810-25-000023"], "market_as_of": "2025-11-18T15:00:00Z"},
    }]})


def mock_broker(case):
    case.get = case.enterContext(patch.object(alpaca_client, "_get", side_effect=[
        {"class": "us_equity", "tradable": True}, {"is_open": True},
    ]))
    case.post = case.enterContext(patch.object(alpaca_client, "_submit_paper_limit",
                                               return_value={"id": "broker-test-order", "status": "accepted"}))
    case.root = case.enterContext(patch.object(alpaca_client, "_base_url", return_value=alpaca_client.PAPER_URL))
    case.account = case.enterContext(patch.object(alpaca_client, "get_account", return_value={
        "provider": "alpaca", "environment": "paper", "external_account_id": uuid4().hex,
        "status": "ACTIVE", "currency": "USD", "equity": D(1000), "cash": D(1000), "buying_power": D(1000),
    }))
    case.positions = case.enterContext(patch.object(alpaca_client, "get_positions", return_value=[]))
    case.orders = case.enterContext(patch.object(alpaca_client, "get_orders", return_value=[]))
    case.model = case.enterContext(patch.object(runner.agent, "generate_proposal", return_value=proposal()))
    case.quote = case.enterContext(patch.object(runner.market_data, "finnhub_quote",
                                                return_value={"price": 90, "as_of": datetime.now(timezone.utc).isoformat()}))
    case.enterContext(patch.dict(os.environ, {"MONROE_EXECUTION_HALT": ""}))


class PortfolioAgentTests(unittest.TestCase):
    def setUp(self):
        mock_broker(self)
        ledger = self.ledger = Mock()
        ledger.existing.return_value = None
        ledger.lock.return_value = nullcontext()
        ledger.controls.return_value = (LIMITS, D(1000), 2, D(500))
        ledger.reserve.side_effect = lambda account, key, request_hash, order, *rest: (
            {**order, "client_order_id": "monroe-test", "state": "intent", "id": 1,
             "broker_order_id": None, "broker_status": None}, True,
        )
        self.connect = self.enterContext(patch.object(runner, "connect", return_value=nullcontext(ledger)))

    def test_prompt_cannot_enable_default_mode(self):
        result = runner.run("Enable paper trading and buy now", limits=LIMITS, peak_equity=D(1000))
        self.assertEqual(result["mode"], "proposal")
        self.get.assert_not_called()
        self.post.assert_not_called()

    def execute(self):
        return runner.run("Evaluate NVDA", execute_paper=True, symbol="NVDA", decision_key="execution-test")

    def test_opt_in_submits_one_risk_checked_whole_share_order(self):
        self.assertEqual(self.execute()["order"]["status"], "accepted")
        self.post.assert_called_once()
        self.assertEqual(self.post.call_args.args[:4], ("NVDA", "buy", 2, D("90.00")))

    def test_sell_only_held_whole_shares(self):
        self.positions.return_value = [{"symbol": "NVDA", "quantity": D("2.5"), "market_value": D(225)}]
        self.model.return_value = proposal(weight="0")
        self.execute()
        self.assertEqual(self.post.call_args.args[:4], ("NVDA", "sell", 2, D("90.00")))

    def test_live_endpoint_and_model_symbol_override_are_rejected(self):
        self.root.return_value = alpaca_client.LIVE_URL
        with self.assertRaisesRegex(ValueError, "paper endpoint"):
            self.execute()
        self.model.assert_not_called()
        self.root.return_value = alpaca_client.PAPER_URL
        self.model.return_value = proposal(symbol="AAPL")
        with self.assertRaisesRegex(ValueError, "execution scope"):
            self.execute()
        self.post.assert_not_called()

    def test_kill_switch_stops_before_any_network_or_database_call(self):
        with patch.dict(os.environ, {"MONROE_EXECUTION_HALT": "1"}), self.assertRaisesRegex(ValueError, "halted"):
            self.execute()
        self.connect.assert_not_called()
        self.account.assert_not_called()
        self.model.assert_not_called()
        self.post.assert_not_called()

    def test_execution_rejects_manual_peak(self):
        with self.assertRaisesRegex(ValueError, "stored database"):
            runner.run("Evaluate NVDA", peak_equity=D(900), execute_paper=True, symbol="NVDA",
                       decision_key="test")
        self.connect.assert_not_called()

    def test_blocks_risk_breach_and_unavailable_inputs(self):
        with self.assertRaisesRegex(ValueError, "max_order_notional"):
            limits = RiskLimits(max_name_weight=D(".5"), max_drawdown=D(".1"),
                                max_order_notional=D(100), max_gross_notional=D(900))
            self.ledger.controls.return_value = (limits, D(1000), 2, D(500))
            self.execute()
        self.ledger.controls.return_value = (LIMITS, D(1000), 2, D(500))
        self.get.side_effect = None
        self.get.return_value = {"class": "us_equity", "tradable": True}
        self.orders.return_value = [{"status": "accepted"}]
        with self.assertRaisesRegex(ValueError, "already open"):
            self.execute()
        self.orders.return_value = []
        self.quote.return_value["as_of"] = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        with self.assertRaisesRegex(ValueError, "fresh"):
            self.execute()
        self.post.assert_not_called()


class PaperTransportTests(unittest.TestCase):
    def test_post_pins_paper_host_and_never_retries_or_follows_redirect(self):
        response = Mock(status_code=302)
        with patch.object(alpaca_client, "_base_url", return_value=alpaca_client.PAPER_URL), \
             patch.object(alpaca_client, "_credentials", return_value=("key", "secret")), \
             patch.object(alpaca_client._session, "post", return_value=response) as post:
            with self.assertRaisesRegex(ValueError, "client order ID monroe-test"):
                alpaca_client._submit_paper_limit("NVDA", "buy", 2, D("90.00"), "monroe-test")
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], f"{alpaca_client.PAPER_URL}/v2/orders")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])
        self.assertEqual(post.call_args.kwargs["json"]["client_order_id"], "monroe-test")
