"""Read just the Alpaca fields used by portfolio risk."""

from dataclasses import dataclass
from decimal import Decimal

import alpaca_client
from risk import Position


@dataclass(frozen=True)
class PortfolioView:
    equity: Decimal
    peak_equity: Decimal
    positions: tuple[Position, ...]


def read_portfolio(peak_equity: Decimal) -> PortfolioView:
    """Use a peak supplied by the caller's trusted equity history."""
    if not isinstance(peak_equity, Decimal) or not peak_equity.is_finite() or peak_equity <= 0:
        raise ValueError("A positive historical peak equity is required")
    account = alpaca_client.get_account()
    equity = account["equity"]
    if account["currency"] != "USD" or not isinstance(equity, Decimal) or not equity.is_finite() or equity <= 0:
        raise ValueError("Portfolio risk requires positive USD equity")
    positions = []
    for row in alpaca_client.get_positions():
        value = row["market_value"]
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ValueError("An open position is missing a finite market value")
        positions.append(Position(row["symbol"], None, value))
    return PortfolioView(equity, max(peak_equity, equity), tuple(positions))
