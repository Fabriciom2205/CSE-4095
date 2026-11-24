"""Pure portfolio risk calculations for exposures in one account currency."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext
from fractions import Fraction


ZERO = Decimal(0)
ONE = Decimal(1)


def _finite(value: Decimal, name: str) -> Decimal:
    if type(value) is int:
        value = Decimal(value)
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")
    return value


def _nonnegative(value: Decimal, name: str) -> Decimal:
    value = _finite(value, name)
    if value < ZERO:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _positive(value: Decimal, name: str) -> Decimal:
    value = _finite(value, name)
    if value <= ZERO:
        raise ValueError(f"{name} must be positive")
    return value


def _weight(value: Decimal, name: str) -> Decimal:
    value = _nonnegative(value, name)
    if value > ONE:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def size_notional(budget: Decimal, price: Decimal) -> int:
    """Return the maximum whole shares affordable at price."""
    budget = _nonnegative(budget, "budget")
    price = _positive(price, "price")
    return Fraction(budget) // Fraction(price)


def size_at_stop(
    equity: Decimal,
    risk_fraction: Decimal,
    entry_price: Decimal,
    stop_price: Decimal,
    *,
    notional_cap: Decimal | None = None,
) -> int:
    """Size whole shares by equity at risk over the absolute entry-to-stop distance."""
    equity = _nonnegative(equity, "equity")
    risk_fraction = _weight(risk_fraction, "risk_fraction")
    entry = _positive(entry_price, "entry_price")
    stop = _positive(stop_price, "stop_price")
    distance = abs(Fraction(entry) - Fraction(stop))
    if distance == 0:
        raise ValueError("stop_price must differ from entry_price")
    quantity = (Fraction(equity) * Fraction(risk_fraction)) // distance
    return quantity if notional_cap is None else min(quantity, size_notional(notional_cap, entry))


def _decimal(value: Fraction) -> Decimal:
    with localcontext(Context(prec=50)):
        return Decimal(value.numerator) / Decimal(value.denominator)


def _drawdown(equity: Decimal, peak_equity: Decimal) -> Fraction:
    equity = Fraction(_finite(equity, "equity"))
    peak = Fraction(_positive(peak_equity, "peak_equity"))
    return max(Fraction(0), (peak - equity) / peak)


def drawdown(equity: Decimal, peak_equity: Decimal) -> Decimal:
    """Return the fraction lost from peak equity, or zero at a new peak."""
    return _decimal(_drawdown(equity, peak_equity))


@dataclass(frozen=True)
class Position:
    symbol: str
    sector: str | None
    market_value: Decimal


@dataclass(frozen=True)
class RiskLimits:
    max_name_weight: Decimal | None = None
    max_sector_weight: Decimal | None = None
    max_order_notional: Decimal | None = None
    max_gross_notional: Decimal | None = None
    max_drawdown: Decimal | None = None

    def __post_init__(self) -> None:
        for name in ("max_name_weight", "max_sector_weight", "max_drawdown"):
            value = getattr(self, name)
            if value is not None:
                _weight(value, name)
        for name in ("max_order_notional", "max_gross_notional"):
            value = getattr(self, name)
            if value is not None:
                _nonnegative(value, name)


@dataclass(frozen=True)
class Concentration:
    gross_notional: Decimal
    name_weights: dict[str, Decimal]
    sector_weights: dict[str | None, Decimal]


def _gross_values(positions: Iterable[Position]) -> tuple[dict[str, Fraction], dict[str | None, Fraction]]:
    names: dict[str, Fraction] = {}
    sectors: dict[str | None, Fraction] = {}
    for position in positions:
        if not isinstance(position.symbol, str) or not position.symbol.strip():
            raise ValueError("position symbol must be nonempty")
        if position.sector is not None and not isinstance(position.sector, str):
            raise ValueError("position sector must be text or None")
        value = abs(Fraction(_finite(position.market_value, "market_value")))
        if not value:
            continue
        symbol = position.symbol.strip().upper()
        sector = (position.sector or "").strip().casefold() or None
        names[symbol] = names.get(symbol, Fraction(0)) + value
        sectors[sector] = sectors.get(sector, Fraction(0)) + value
    return names, sectors


def concentration(positions: Iterable[Position], equity: Decimal) -> Concentration:
    """Measure gross exposures relative to positive account equity.

    Long and short values contribute equally by magnitude. Unknown sectors
    share one bucket.
    """
    equity = Fraction(_positive(equity, "equity"))
    names, sectors = _gross_values(positions)
    return Concentration(
        gross_notional=_decimal(sum(names.values(), Fraction(0))),
        name_weights={symbol: _decimal(value / equity) for symbol, value in names.items()},
        sector_weights={sector: _decimal(value / equity) for sector, value in sectors.items()},
    )


@dataclass(frozen=True)
class Breach:
    limit: str
    actual: Decimal
    maximum: Decimal
    subject: str | None = None


def check_limits(
    positions: Iterable[Position],
    equity: Decimal,
    peak_equity: Decimal,
    limits: RiskLimits,
    *,
    order_notional: Decimal = ZERO,
) -> tuple[Breach, ...]:
    """Check current or caller-projected exposures against inclusive caps.

    None disables a cap. Equity must be positive to measure concentration.
    Comparisons are exact. Decimal values in the report are for display.
    """
    equity = _positive(equity, "equity")
    denominator = Fraction(equity)
    names, sectors = _gross_values(positions)
    checks = [
        ("max_order_notional", Fraction(_nonnegative(order_notional, "order_notional")), None),
        ("max_gross_notional", sum(names.values(), Fraction(0)), None),
        ("max_drawdown", _drawdown(equity, peak_equity), None),
    ]
    checks.extend(("max_name_weight", value / denominator, symbol) for symbol, value in sorted(names.items()))
    checks.extend(
        ("max_sector_weight", value / denominator, sector)
        for sector, value in sorted(sectors.items(), key=lambda item: item[0] or "")
    )
    breaches = []
    for name, actual, subject in checks:
        limit = getattr(limits, name)
        if limit is not None and actual > Fraction(limit):
            breaches.append(Breach(name, _decimal(actual), _finite(limit, name), subject))
    return tuple(breaches)
