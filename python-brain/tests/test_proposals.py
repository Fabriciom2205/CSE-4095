"""Proposal schema, deterministic order sizing, and private agent regression checks."""

import json
import os
import unittest
from decimal import Decimal as D, localcontext
from unittest.mock import Mock, patch

import agent
import alpaca_client
from portfolio_view import PortfolioView, read_portfolio
from propose import Order, Proposal, build_orders, proposal_breaches
from risk import Position, RiskLimits

TARGET = {
    "symbol": "NVDA",
    "target_weight": 0.2,
    "rationale": "Based on the cited filing and quote.",
    "evidence": {"accessions": ["0001045810-25-000023"], "market_as_of": "2025-11-18T15:00:00Z"},
    "confidence": 0.75,
}


class ProposalTests(unittest.TestCase):
    def test_build_orders_applies_both_caps_and_rounds_down(self):
        limits = RiskLimits(max_name_weight=D(".25"), max_order_notional=D(200))
        weights = {"MSFT": D(".8"), "AAPL": D(".1"), "NVDA": D(".1")}
        prices = {"MSFT": D(30), "AAPL": D(33), "NVDA": D(300)}
        with localcontext() as context:
            context.prec = 2
            self.assertEqual(build_orders(weights, D(1000), prices, limits), (Order("AAPL", 3), Order("MSFT", 6)))
        self.assertEqual(build_orders({"MSFT": D(".8")}, D(1000), {"MSFT": D(30)},
                                      RiskLimits(max_name_weight=D(".25"))), (Order("MSFT", 8),))

    def test_build_orders_rejects_bad_inputs(self):
        for weights, prices in (({"nvda": D("0.1")}, {"nvda": D(10)}),
                                 ({"NVDA": D(".8"), "MSFT": D(".3")}, {}),
                                 ({"NVDA": D(".1")}, {}), ({"NVDA": D(".1")}, {"NVDA": D(0)})):
            with self.subTest(weights=weights, prices=prices), self.assertRaises(ValueError):
                build_orders(weights, D(1000), prices, RiskLimits())

    def test_schema_rejects_breach_duplicate_bad_symbol_and_order_fields(self):
        variants = [
            [{"symbol": f"A{i}"} for i in range(11)],
            [{}, {}],
            [{"symbol": "nvda"}],
            [{"target_weight": 0.6}, {"symbol": "AMD", "target_weight": 0.5}],
            [{"quantity": 4}],
            [{"evidence": {"accessions": ["bad"], "market_as_of": "2025-11-18T15:00:00Z"}}],
        ]
        for targets in variants:
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                Proposal.model_validate({"targets": [TARGET | value for value in targets]})

    def test_portfolio_adapts_signed_exposures_and_requires_reliable_data(self):
        with patch("alpaca_client.get_account", return_value={"currency": "USD", "equity": D(1000)}), \
             patch("alpaca_client.get_positions", return_value=[{"symbol": "NVDA", "market_value": D(-200)}]) as positions:
            self.assertEqual(read_portfolio(D(900)), PortfolioView(D(1000), D(1000), (Position("NVDA", None, D(-200)),)))
            positions.return_value[0]["market_value"] = None
            with self.assertRaisesRegex(ValueError, "market value"):
                read_portfolio(D(1100))

    def test_projection_checks_change_and_retained_holdings(self):
        view = PortfolioView(D(1000), D(1200), (Position("NVDA", None, D(180)), Position("MSFT", None, D(600))))
        proposal = Proposal.model_validate({"targets": [TARGET]})
        limits = RiskLimits(max_gross_notional=D(700), max_name_weight=D(".5"), max_order_notional=D(20))
        findings = proposal_breaches(proposal, view, limits)
        self.assertEqual({(breach.limit, breach.subject) for breach in findings},
                         {("max_name_weight", "MSFT"), ("max_gross_notional", None)})
        with self.assertRaisesRegex(ValueError, "Sector cap"):
            proposal_breaches(proposal, view, RiskLimits(max_sector_weight=D(".5")))

    def test_private_agent_tools_and_final_validation(self):
        view = PortfolioView(D(1000), D(1000), ())
        result = Mock(text=json.dumps({"targets": [TARGET]}))
        with patch.object(agent.google_client, "create_client") as create_client, \
             patch("portfolio_view.read_portfolio", return_value=view) as read:
            client = create_client.return_value
            client.chats.create.return_value.send_message.return_value = result
            proposal = agent.generate_proposal("test", limits=RiskLimits(), peak_equity=D(1000))
            self.assertEqual(proposal.target_weights(), {"NVDA": D(".2")})
            config = client.chats.create.call_args.kwargs["config"]
            self.assertEqual(config.response_mime_type, "application/json")
            snapshot, validate = config.tools[-2:]
            self.assertEqual((snapshot.__name__, validate.__name__), ("portfolio_snapshot", "validate_proposal"))
            self.assertEqual(snapshot()["data"], {"equity": "1000", "peak_equity": "1000", "positions": []})
            self.assertEqual(validate(result.text), {"breaches": []})
            self.assertEqual(read.call_count, 2)
            with self.assertRaisesRegex(ValueError, "Proposal breaches max_name_weight"):
                agent.generate_proposal("test", limits=RiskLimits(max_name_weight=D(".1")), peak_equity=D(1000))
            result.text = '{"targets":[{"quantity":4}]}'
            with self.assertRaisesRegex(ValueError, "invalid proposal"):
                agent.generate_proposal("test", limits=RiskLimits(), peak_equity=D(1000))

    def test_versioned_paper_url_still_uses_the_official_root(self):
        with patch.dict(os.environ, {"ALPACA_BASE_URL": f"{alpaca_client.PAPER_URL}/v2/"}):
            self.assertEqual(alpaca_client._base_url(), alpaca_client.PAPER_URL)


if __name__ == "__main__":
    unittest.main()
