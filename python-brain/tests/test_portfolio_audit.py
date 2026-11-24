"""Durability and reconciliation against disposable PostgreSQL and a mocked broker."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import alpaca_client as broker
import portfolio_agent as runner
import portfolio_store as store
from tests.test_portfolio_agent import mock_broker, proposal


@unittest.skipUnless(os.getenv("MONROE_PORTFOLIO_TEST_DSN"), "requires disposable PostgreSQL migration 004")
class DurableExecutionTests(unittest.TestCase):
    def setUp(self):
        mock_broker(self)
        self.enterContext(patch.dict(os.environ, {"MONROE_PORTFOLIO_DSN": os.environ["MONROE_PORTFOLIO_TEST_DSN"]}))
        self.key = uuid4().hex
        with store.connect() as ledger:
            self.account_id = ledger.account(self.account.return_value)
            ledger.record_equity(self.account_id, D(1000))
            ledger.conn.execute(
                """INSERT INTO portfolio.risk_limit
                     (account_id, max_name_weight, max_gross_notional, max_order_notional,
                      max_drawdown, max_daily_orders, max_daily_notional)
                   VALUES (%s, .5, 900, 300, .1, 1, 500)""", (self.account_id,),
            )

    def execute(self, key=None):
        return runner.run("Evaluate NVDA", execute_paper=True, symbol="NVDA", decision_key=key or self.key)["order"]

    def row(self):
        with store.connect() as ledger:
            return ledger.existing(self.key, store.digest({"symbol": "NVDA", "prompt": "Evaluate NVDA"}))

    def reconcile_fill(self, *, filled=True):
        order = {"id": "broker-test-order", "status": "filled", "symbol": "NVDA",
                 "side": "buy", "filled_quantity": D(2)}
        fill = {"id": "activity-1", "symbol": "NVDA", "side": "buy", "quantity": D(2),
                "price": D(90), "executed_at": datetime.now(timezone.utc)}
        with patch.object(broker, "_paper_order", return_value=order), \
             patch.object(broker, "_paper_fills", return_value=[fill] if filled else []):
            return runner.reconcile()

    def next_decision(self):
        self.get.side_effect = [{"class": "us_equity", "tradable": True}, {"is_open": True}]
        self.model.return_value = proposal(weight="0.3")
        return self.execute(uuid4().hex)

    def test_repeat_returns_stored_id_without_new_provider_reads(self):
        first = self.execute()
        second = self.execute()
        self.assertEqual(first["client_order_id"], second["client_order_id"])
        self.assertTrue(second["duplicate"])
        self.post.assert_called_once()
        self.model.assert_called_once()
        self.assertIn("quote_as_of", self.row()["risk_inputs"])

    def test_crash_after_intent_before_post_is_durable(self):
        def fail_before_network(*args):
            self.assertEqual(self.row()["state"], "intent")
            raise RuntimeError("crash before socket opens")
        self.post.side_effect = fail_before_network
        with self.assertRaisesRegex(RuntimeError, "before socket"):
            self.execute()
        self.assertEqual(self.row()["state"], "intent")
        self.assertTrue(self.execute()["duplicate"])
        self.post.assert_called_once()

    def test_crash_after_post_is_adopted_and_fills_are_idempotent(self):
        with patch.object(store.Ledger, "submission", side_effect=RuntimeError("crash before update")):
            with self.assertRaisesRegex(RuntimeError, "before update"):
                self.execute()
        self.assertEqual(self.row()["state"], "intent")
        self.assertEqual(self.reconcile_fill(filled=False), {"inspected": 1, "settled": 0})
        self.assertEqual(self.row()["broker_status"], "filled")
        self.assertEqual(self.reconcile_fill(), {"inspected": 1, "settled": 1})
        self.assertEqual(self.reconcile_fill(), {"inspected": 0, "settled": 0})
        with store.connect() as ledger:
            total = ledger.conn.execute("SELECT count(*) AS n FROM portfolio.trade WHERE account_id = %s",
                                        (self.account_id,)).fetchone()["n"]
        self.assertEqual(total, 1)
        self.post.assert_called_once()

    def test_ambiguous_post_is_unknown_and_not_retried(self):
        self.post.side_effect = broker.AlpacaError("timeout")
        first = self.execute()
        self.assertEqual(first["state"], "unknown")
        self.assertEqual(self.execute()["client_order_id"], first["client_order_id"])
        self.post.assert_called_once()

    def test_stored_peak_triggers_drawdown_breach(self):
        with store.connect() as ledger:
            ledger.record_equity(self.account_id, D(1250))
        with self.assertRaisesRegex(ValueError, "max_drawdown"):
            self.execute()
        self.assertEqual(self.model.call_args.kwargs["peak_equity"], D(1250))

    def test_projected_sector_breach_blocks_paper_submission(self):
        with store.connect() as ledger:
            ledger.conn.execute("UPDATE portfolio.risk_limit SET max_sector_weight = .1 WHERE account_id = %s",
                                (self.account_id,))
        with patch("portfolio_sectors.classifications", return_value={"NVDA": "manufacturing"}):
            with self.assertRaisesRegex(ValueError, "max_sector_weight"):
                self.execute()
        self.post.assert_not_called()

    def test_read_only_peak_is_scoped_to_account_and_observation_time(self):
        now = datetime.now(timezone.utc)
        external_id = self.account.return_value["external_account_id"]
        with store.connect() as ledger:
            ledger.conn.execute(
                "INSERT INTO portfolio.equity_snapshot VALUES (%s, %s, 2000)",
                (self.account_id, now + timedelta(days=1)),
            )
        with patch.dict(os.environ, {"MONROE_PORTFOLIO_READ_DSN": os.environ["MONROE_PORTFOLIO_TEST_DSN"]}):
            self.assertEqual(store.read_peak_equity("paper", external_id, now), D(1000))
            with self.assertRaisesRegex(ValueError, "Seed trusted equity history"):
                store.read_peak_equity("live", external_id, now)
        self.post.assert_not_called()

    def test_daily_order_cap_blocks_different_decision_after_first_fills(self):
        self.execute()
        self.reconcile_fill()
        with self.assertRaisesRegex(ValueError, "daily ledger cap"):
            self.next_decision()
        self.post.assert_called_once()

    def test_daily_notional_cap_blocks_below_count_cap(self):
        with store.connect() as ledger:
            ledger.conn.execute(
                "UPDATE portfolio.risk_limit SET max_daily_orders = 3, max_daily_notional = 400 WHERE account_id = %s",
                (self.account_id,),
            )
        self.execute()
        self.reconcile_fill()
        with self.assertRaisesRegex(ValueError, "daily ledger cap"):
            self.next_decision()
        self.post.assert_called_once()

    def test_advisory_lock_rejects_other_connections(self):
        with store.connect() as ledger, ledger.lock(self.account_id):
            with self.assertRaisesRegex(ValueError, "Another execution"):
                self.execute()
        self.post.assert_not_called()

    def test_equal_decision_binds_second_key_before_daily_gate(self):
        first = self.execute()
        self.reconcile_fill()
        self.get.side_effect = [{"class": "us_equity", "tradable": True}, {"is_open": True}]
        alias = uuid4().hex
        self.assertTrue(self.execute(alias)["duplicate"])
        repeated = self.execute(alias)
        self.assertEqual(first["client_order_id"], repeated["client_order_id"])
        self.post.assert_called_once()
