"""Parameters for long-only strategies and the daily moving-average signal."""

from dataclasses import dataclass
from decimal import Decimal
import re
from typing import Literal, Sequence

StrategyKind = Literal["moving_average", "momentum", "quality_value", "sentiment"]


@dataclass(frozen=True)
class Strategy:
    symbols: tuple[str, ...]
    lookback_sessions: int = 20
    allocation_fraction: Decimal = Decimal("0.25")
    stop_loss_fraction: Decimal = Decimal("0.10")
    kind: StrategyKind = "moving_average"
    top_n: int = 1

    def __post_init__(self):
        if (not isinstance(self.symbols, tuple) or not 1 <= len(self.symbols) <= 10
                or any(not isinstance(symbol, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol)
                       for symbol in self.symbols)
                or len(set(self.symbols)) != len(self.symbols)):
            raise ValueError("Universe must contain 1 to 10 unique uppercase stock symbols")
        if type(self.lookback_sessions) is not int or not 2 <= self.lookback_sessions <= 200:
            raise ValueError("Lookback must be between 2 and 200 sessions")
        if self.kind not in ("moving_average", "momentum", "quality_value", "sentiment"):
            raise ValueError("Unknown strategy type")
        if type(self.top_n) is not int or not 1 <= self.top_n <= 10:
            raise ValueError("Number of selections must be between 1 and 10")
        if self.kind != "moving_average" and self.top_n > len(self.symbols):
            raise ValueError("Number of selections cannot exceed the number of symbols")
        for label, value in (("Allocation", self.allocation_fraction), ("Stop loss", self.stop_loss_fraction)):
            if not isinstance(value, Decimal) or not value.is_finite() or not 0 < value <= 1:
                raise ValueError(f"{label} must be a Decimal fraction greater than 0 and at most 1")


def close_signal(strategy: Strategy, closes: Sequence[Decimal], entry_price: Decimal | None) -> str | None:
    """Decide at the close using only prices observed through that session."""
    if len(closes) < strategy.lookback_sessions:
        return None
    close = closes[-1]
    average = sum(closes[-strategy.lookback_sessions:]) / strategy.lookback_sessions
    if entry_price is None:
        return "buy" if close > average else None
    if close < average or close <= entry_price * (1 - strategy.stop_loss_fraction):
        return "sell"
    return None
