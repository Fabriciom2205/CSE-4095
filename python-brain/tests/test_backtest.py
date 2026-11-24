"""Offline fixtures for deterministic strategy and Massive snapshot tests."""

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import unittest
from unittest.mock import patch

import backtest
import market_data
from strategy import Strategy


def year_fixture() -> dict:
    start, end = date(2025, 1, 1), date(2025, 12, 31)
    bars = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        if day.weekday() < 5:
            price = 120 if (len(bars) // 30) % 2 else 100
            bars.append({"date": day.isoformat(), "open": price, "close": price})
    return {"source": "synthetic", "adjusted": False, "start": start.isoformat(), "end": end.isoformat(),
            "bars": {"TEST": bars}}


class BacktestTests(unittest.TestCase):
    def test_full_year_replay_is_reproducible(self):
        snapshot = year_fixture()
        strategy = Strategy(("TEST",))
        first = backtest.replay(strategy, snapshot)
        self.assertEqual(first, backtest.replay(strategy, deepcopy(snapshot)))
        self.assertEqual(len(first["equity_curve"]), 261)
        self.assertEqual(len(first["fills"]), 8)
        self.assertEqual(Decimal(first["final_equity"]), Decimal("8460"))
        self.assertEqual(Decimal(first["max_drawdown"]), Decimal("0.154"))

    def test_first_order_size_uses_signal_close_and_fill_uses_next_open(self):
        snapshot = year_fixture()
        rows = snapshot["bars"]["TEST"]
        rows[31]["open"] = 170
        rows[31]["close"] = 5
        result = backtest.replay(Strategy(("TEST",)), snapshot)
        fill = result["fills"][0]
        self.assertEqual(fill, {"symbol": "TEST", "side": "buy", "quantity": 20, "price": "170",
                                "signal_date": rows[30]["date"], "fill_date": rows[31]["date"]})
        self.assertEqual(result["fills"][1]["signal_date"], rows[31]["date"])
        self.assertEqual(result["fills"][1]["fill_date"], rows[32]["date"])

    def test_rejects_adjusted_and_conflicting_bars(self):
        snapshot = year_fixture()
        strategy = Strategy(("TEST",))
        with self.assertRaisesRegex(ValueError, "raw"):
            backtest.replay(strategy, {**snapshot, "adjusted": True})
        snapshot["bars"]["TEST"].append(snapshot["bars"]["TEST"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            backtest.replay(strategy, snapshot)

    def test_capture_checks_splits_and_requests_unadjusted_bars(self):
        args = ("2025-01-01", "2025-12-31")
        with patch.object(market_data, "massive_splits", return_value=[]) as splits, \
             patch.object(market_data, "massive_daily_bars", return_value={"bars": year_fixture()["bars"]["TEST"]}) as bars:
            snapshot = backtest.capture_massive(Strategy(("TEST",)), *args)
            self.assertEqual(snapshot["source"], "Massive")
            self.assertIs(snapshot["adjusted"], False)
            splits.assert_called_once_with("TEST", *args)
            bars.assert_called_once_with("TEST", *args, adjusted=False)
            splits.return_value = [{"execution_date": "2025-03-05"}]
            bars.reset_mock()
            with self.assertRaisesRegex(ValueError, "split"):
                backtest.capture_massive(Strategy(("TEST",)), *args)
            bars.assert_not_called()

    def test_massive_snapshot_endpoints_and_pagination_safety(self):
        args = ("2025-01-01", "2025-12-31")
        with patch.object(market_data, "_get", return_value={}) as get:
            self.assertFalse(market_data.massive_daily_bars("TEST", *args, adjusted=False)["adjusted"])
            self.assertEqual(get.call_args.args[2]["adjusted"], "false")
            self.assertEqual(market_data.massive_splits("TEST", *args), [])
            self.assertTrue(get.call_args.args[1].endswith("/stocks/v1/splits"))
            self.assertEqual(get.call_args.args[2]["execution_date.gte"], args[0])
            self.assertEqual(get.call_args.args[2]["execution_date.lte"], args[1])
            get.return_value = {"next_url": "https://other.example"}
            with self.assertRaisesRegex(ValueError, "incomplete split"):
                market_data.massive_splits("TEST", *args)
            with self.assertRaisesRegex(ValueError, "incomplete bar"):
                market_data.massive_daily_bars("TEST", *args, adjusted=False)


if __name__ == "__main__":
    unittest.main()
