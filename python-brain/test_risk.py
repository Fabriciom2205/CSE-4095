"""Limit and breach cases for the deterministic portfolio risk core."""

from decimal import Decimal, localcontext
import unittest

from risk import Position, RiskLimits, check_limits, concentration, drawdown, size_at_stop, size_notional


D = Decimal


class SizingTests(unittest.TestCase):
    def test_notional_sizing_rounds_down_without_exceeding_budget(self):
        self.assertEqual(size_notional(D("99.99"), D("10")), 9)
        self.assertEqual(size_notional(D("100"), D("10")), 10)
        self.assertEqual(size_notional(D("0"), D("10")), 0)

    def test_stop_sizing_uses_both_risk_and_notional_caps(self):
        self.assertEqual(size_at_stop(D("10000"), D("0.01"), D("100"), D("96")), 25)
        self.assertEqual(size_at_stop(D("10000"), D("0.01"), D("100"), D("104"),
                                      notional_cap=D("1999.99")), 19)
        self.assertEqual(size_at_stop(D("10000"), D("0"), D("100"), D("96")), 0)

    def test_invalid_price_stop_and_risk_fraction_are_rejected(self):
        for value in (D("0"), D("-1"), D("NaN"), D("Infinity"), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                size_notional(D("100"), value)
        with self.assertRaisesRegex(ValueError, "differ"):
            size_at_stop(D("10000"), D("0.01"), D("100"), D("100"))
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            size_at_stop(D("10000"), D("1.01"), D("100"), D("96"))


class LimitTests(unittest.TestCase):
    def setUp(self):
        self.positions = [
            Position("aapl", "Technology", D("200")),
            Position(" AAPL ", "technology", D("-100")),
            Position("MSFT", "Technology", D("100")),
            Position("X", None, D("100")),
            Position("Y", "", D("-100")),
        ]

    def test_concentration_uses_gross_exposure_and_unknown_sector_bucket(self):
        report = concentration(iter(self.positions), D("1000"))
        self.assertEqual(report.gross_notional, D("600"))
        self.assertEqual(report.name_weights, {"AAPL": D("0.3"), "MSFT": D("0.1"),
                                               "X": D("0.1"), "Y": D("0.1")})
        self.assertEqual(report.sector_weights, {"technology": D("0.4"), None: D("0.2")})

    def test_limits_are_inclusive(self):
        limits = RiskLimits(D("0.3"), D("0.4"), D("100"), D("600"), D("0.2"))
        self.assertEqual(check_limits(self.positions, D("1000"), D("1250"), limits,
                                      order_notional=D("100")), ())

    def test_limit_breaches_identify_actual_maximum_and_subject(self):
        limits = RiskLimits(D("0.29"), D("0.39"), D("99"), D("599"), D("0.19"))
        breaches = check_limits(self.positions, D("1000"), D("1250"), limits, order_notional=D("100"))
        self.assertEqual(
            [(b.limit, b.actual, b.maximum, b.subject) for b in breaches],
            [("max_order_notional", D("100"), D("99"), None),
             ("max_gross_notional", D("600"), D("599"), None),
             ("max_drawdown", D("0.2"), D("0.19"), None),
             ("max_name_weight", D("0.3"), D("0.29"), "AAPL"),
             ("max_sector_weight", D("0.4"), D("0.39"), "technology")],
        )

    def test_exact_threshold_checks_are_independent_of_decimal_context(self):
        positions = [Position("AAPL", None, D("1"))]
        with localcontext() as context:
            context.prec = 2
            breaches = check_limits(positions, D("3"), D("3"), RiskLimits(max_name_weight=D("0.3333333")))
        self.assertEqual(breaches[0].limit, "max_name_weight")
        self.assertGreater(breaches[0].actual, breaches[0].maximum)

    def test_zero_is_a_limit_and_none_disables_limits(self):
        limits = RiskLimits(max_order_notional=D("0"))
        self.assertEqual(len(check_limits((), D("100"), D("100"), limits, order_notional=D("1"))), 1)
        self.assertEqual(check_limits(self.positions, D("100"), D("500"), RiskLimits()), ())

    def test_drawdown_starts_at_zero_and_tracks_equity_below_peak(self):
        self.assertEqual(drawdown(D("101"), D("100")), D("0"))
        self.assertEqual(drawdown(D("75"), D("100")), D("0.25"))
        self.assertEqual(drawdown(D("-10"), D("100")), D("1.1"))

    def test_invalid_limits_exposures_and_references_are_rejected(self):
        with self.assertRaises(ValueError):
            RiskLimits(max_drawdown=D("1.1"))
        with self.assertRaises(ValueError):
            RiskLimits(max_gross_notional=D("-0.01"))
        with self.assertRaises(ValueError):
            concentration(self.positions, D("0"))
        with self.assertRaisesRegex(ValueError, "equity must be positive"):
            check_limits((), D("-1"), D("100"), RiskLimits())
        with self.assertRaises(ValueError):
            concentration([Position("AAPL", None, D("Infinity"))], D("100"))
        with self.assertRaises(ValueError):
            drawdown(D("100"), D("0"))


if __name__ == "__main__":
    unittest.main()
