"""Proposal schema and deterministic hypothetical sizing and validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Context, Decimal, localcontext
from fractions import Fraction
import re
from typing import Annotated, TYPE_CHECKING

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, WithJsonSchema, model_validator

from risk import Breach, Position, RiskLimits, check_limits

if TYPE_CHECKING:
    from portfolio_view import PortfolioView

SYMBOL = r"^[A-Z][A-Z0-9.-]{0,9}$"
ACCESSION = r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
MAX_SYMBOLS = 10
UnitFraction = Annotated[
    Decimal, Field(ge=0, le=1, allow_inf_nan=False),
    WithJsonSchema({"type": "number", "minimum": 0, "maximum": 1}, mode="validation"),
]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accessions: list[Annotated[str, Field(pattern=ACCESSION)]] = Field(min_length=1, max_length=10)
    market_as_of: AwareDatetime


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(pattern=SYMBOL)
    target_weight: UnitFraction
    rationale: str = Field(min_length=1, max_length=2000)
    evidence: Evidence
    confidence: UnitFraction


def _checked_weights(weights: Mapping[str, Decimal]) -> dict[str, Fraction]:
    if len(weights) > MAX_SYMBOLS:
        raise ValueError("At most 10 symbols are allowed")
    checked = {}
    for symbol, value in weights.items():
        if not isinstance(symbol, str) or not re.fullmatch(SYMBOL, symbol):
            raise ValueError("Invalid proposal symbol")
        weight = _number(value, "Target weight")
        if not 0 <= weight <= 1:
            raise ValueError("Target weights must be between 0 and 1")
        checked[symbol] = weight
    if sum(checked.values()) > 1:
        raise ValueError("Target weights must sum to at most 1")
    return checked


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    targets: list[Target] = Field(max_length=MAX_SYMBOLS)

    def target_weights(self) -> dict[str, Decimal]:
        return {target.symbol: target.target_weight for target in self.targets}

    @model_validator(mode="after")
    def check_weights(self):
        weights = self.target_weights()
        if len(weights) != len(self.targets):
            raise ValueError("Proposal contains duplicate symbols")
        _checked_weights(weights)
        return self


def _number(value: Decimal, label: str) -> Fraction:
    if type(value) is int:
        return Fraction(value)
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{label} must be a finite Decimal")
    return Fraction(value)


@dataclass(frozen=True)
class Order:
    symbol: str
    quantity: int


def build_orders(target_weights: Mapping[str, Decimal], equity: Decimal,
                 prices: Mapping[str, Decimal], limits: RiskLimits) -> tuple[Order, ...]:
    """Construct whole-share hypothetical buys from cash. No broker access."""
    weights = _checked_weights(target_weights)
    capital = _number(equity, "Equity")
    if capital <= 0:
        raise ValueError("Equity must be positive")
    orders = []
    for symbol, weight in sorted(weights.items()):
        if not weight:
            continue
        if symbol not in prices:
            raise ValueError(f"Missing price for {symbol}")
        price = _number(prices[symbol], "Price")
        if price <= 0:
            raise ValueError("Price must be positive")
        if limits.max_name_weight is not None:
            weight = min(weight, Fraction(limits.max_name_weight))
        budget = capital * weight
        if limits.max_order_notional is not None:
            budget = min(budget, Fraction(limits.max_order_notional))
        quantity = budget // price
        if quantity:
            orders.append(Order(symbol, quantity))
    return tuple(orders)


def proposal_breaches(proposal: Proposal, view: PortfolioView, limits: RiskLimits) -> tuple[Breach, ...]:
    """Check projected exposures and the largest dollar change to a named holding."""
    if limits.max_sector_weight is not None:
        raise ValueError("Sector cap cannot be evaluated without sector classifications")
    weights = proposal.target_weights()
    with localcontext(Context(prec=64)):
        projected = [position for position in view.positions if position.symbol not in weights]
        largest_change = Decimal(0)
        for symbol, weight in weights.items():
            target_value = view.equity * weight
            current_value = sum((p.market_value for p in view.positions if p.symbol == symbol), Decimal(0))
            largest_change = max(largest_change, abs(target_value - current_value))
            projected.append(Position(symbol, None, target_value))
        return check_limits(projected, view.equity, view.peak_equity, limits, order_notional=largest_change)
