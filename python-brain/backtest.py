"""Capture Massive daily bars and replay a fixed universe with next-open fills."""

import argparse
from dataclasses import asdict
from datetime import date, datetime
from decimal import Context, Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import market_data
from risk import drawdown, size_notional
from strategy import Strategy, close_signal


def _date(value: str) -> date:
    day = date.fromisoformat(value)
    if day.isoformat() != value:
        raise ValueError("Dates must use YYYY-MM-DD")
    return day


def _window(start: str, end: str) -> tuple[date, date]:
    since, until = _date(start), _date(end)
    if not 1 <= (until - since).days <= market_data.MAX_RANGE_DAYS:
        raise ValueError("Replay must span between 1 and 366 calendar days")
    return since, until


def _positive_decimal(value, label: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a positive finite number") from None
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{label} must be a positive finite number")
    return number


def capture_massive(strategy: Strategy, start: str, end: str) -> dict:
    """Get a bounded raw bar snapshot and check for share-count changes."""
    _, until = _window(start, end)
    if until >= datetime.now(ZoneInfo("America/New_York")).date():
        raise ValueError("Capture end must be before today to exclude unfinished bars")
    series = {}
    for symbol in strategy.symbols:
        # shortcut: reject share-count changes until replay can apply corporate actions on their effective dates.
        if market_data.massive_splits(symbol, start, end):
            raise ValueError(f"{symbol} has a split or stock dividend during the replay window")
        bars = market_data.massive_daily_bars(symbol, start, end, adjusted=False)
        if not bars["bars"]:
            raise ValueError(f"Massive returned no daily bars for {symbol}")
        series[symbol] = [{"date": row["date"], "open": row["open"], "close": row["close"]}
                          for row in bars["bars"]]
    return {"source": "Massive", "adjusted": False, "start": start, "end": end, "bars": series}


def _series(snapshot: dict, strategy: Strategy) -> dict:
    since, until = _window(snapshot["start"], snapshot["end"])
    if snapshot.get("adjusted") is not False:
        raise ValueError("Replay requires raw daily bars")
    series = {}
    for symbol in strategy.symbols:
        rows = snapshot["bars"].get(symbol, [])
        bars = {}
        for row in rows:
            day = _date(row["date"])
            if day in bars or not since <= day <= until:
                raise ValueError(f"{symbol} has duplicate or out-of-window bars")
            bars[day] = (_positive_decimal(row["open"], "Open"), _positive_decimal(row["close"], "Close"))
        if len(bars) < strategy.lookback_sessions + 1:
            raise ValueError(f"{symbol} has too few bars for a replay with this lookback")
        if series and bars.keys() != next(iter(series.values())).keys():
            raise ValueError("Universe symbols must have the same session dates")
        series[symbol] = bars
    return series


def replay(strategy: Strategy, snapshot: dict, initial_cash: Decimal = Decimal("10000")) -> dict:
    """Simulate a fixed strategy on the supplied snapshot, without live calls."""
    with localcontext(Context(prec=34)):
        return _replay(strategy, snapshot, _positive_decimal(initial_cash, "Initial cash"))


def _replay(strategy: Strategy, snapshot: dict, initial_cash: Decimal) -> dict:
    series = _series(snapshot, strategy)
    symbols = tuple(sorted(strategy.symbols))
    dates = sorted(series[symbols[0]])
    cash = peak = initial_cash
    max_drawdown = Decimal(0)
    closes = {symbol: [] for symbol in symbols}
    positions = {}
    pending = []
    fills = []
    curve = []
    for day in dates:
        # Fill quantities are fixed at the previous close. Process exits before entries.
        for symbol, action, quantity, signal_day in sorted(pending, key=lambda order: order[1] != "sell"):
            opening_price = series[symbol][day][0]
            notional = quantity * opening_price
            if action == "sell":
                cash += notional
                del positions[symbol]
            elif notional <= cash:
                cash -= notional
                positions[symbol] = (quantity, opening_price)
            else:
                continue
            fills.append({"symbol": symbol, "side": action, "quantity": quantity, "price": str(opening_price),
                          "signal_date": signal_day.isoformat(), "fill_date": day.isoformat()})
        for symbol in symbols:
            closes[symbol].append(series[symbol][day][1])
        equity = cash + sum(quantity * closes[symbol][-1] for symbol, (quantity, _) in positions.items())
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, drawdown(equity, peak))
        curve.append({"date": day.isoformat(), "equity": str(equity)})
        pending = []
        for symbol in symbols:
            quantity, entry_price = positions.get(symbol, (0, None))
            signal = close_signal(strategy, closes[symbol], entry_price)
            if signal == "buy":
                quantity = size_notional(equity * strategy.allocation_fraction, closes[symbol][-1])
            if signal and quantity:
                pending.append((symbol, signal, quantity, day))
    digest = sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"source": snapshot["source"], "input_sha256": digest, "start": snapshot["start"], "end": snapshot["end"],
            "strategy": {**asdict(strategy), "symbols": list(strategy.symbols),
                         "allocation_fraction": str(strategy.allocation_fraction),
                         "stop_loss_fraction": str(strategy.stop_loss_fraction)},
            "initial_cash": str(initial_cash), "final_cash": str(cash), "final_equity": str(equity),
            "max_drawdown": str(max_drawdown), "open_positions": {symbol: qty for symbol, (qty, _) in positions.items()},
            "fills": fills, "equity_curve": curve}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="Fetch raw Massive bars and write a snapshot to stdout")
    capture.add_argument("start")
    capture.add_argument("end")
    capture.add_argument("symbols", nargs="+")
    run = commands.add_parser("replay", help="Replay a snapshot and write the result to stdout")
    run.add_argument("snapshot", type=Path)
    run.add_argument("--lookback", type=int, default=20)
    run.add_argument("--allocation", default="0.25")
    run.add_argument("--stop-loss", default="0.10")
    run.add_argument("--initial-cash", default="10000")
    args = parser.parse_args()
    try:
        if args.command == "capture":
            result = capture_massive(Strategy(tuple(args.symbols)), args.start, args.end)
        else:
            snapshot = json.loads(args.snapshot.read_text())
            strategy = Strategy(tuple(sorted(snapshot["bars"])), args.lookback,
                                _positive_decimal(args.allocation, "Allocation"),
                                _positive_decimal(args.stop_loss, "Stop loss"))
            result = replay(strategy, snapshot, args.initial_cash)
    except (KeyError, TypeError, ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
