"""Run proposal mode by default or explicitly opt in to one Alpaca paper order."""

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, DecimalException, localcontext
import json
import re
import os

import agent
import alpaca_client as broker
import market_data
import portfolio_sectors
from propose import Proposal, SYMBOL
from portfolio_store import connect, digest
from risk import Position, RiskLimits, check_limits, classified_positions, size_notional


def _ensure_running():
    if os.getenv("MONROE_EXECUTION_HALT", "").strip():
        raise ValueError("Paper execution is halted by MONROE_EXECUTION_HALT")


def _paper_account():
    if broker._base_url() != broker.PAPER_URL:
        raise ValueError("Execution requires the Alpaca paper endpoint")
    account = broker.get_account()
    if (account["environment"] != "paper" or account["currency"] != "USD"
            or account["equity"] is None or account["equity"] <= 0):
        raise ValueError("Paper execution requires positive USD equity on the paper account")
    return account


def _result(row, *, duplicate=False):
    return {"client_order_id": row["client_order_id"], "state": row["state"], "duplicate": duplicate,
            "id": row["broker_order_id"], "status": row["broker_status"], "symbol": row["symbol"],
            "side": row["side"], "quantity": row["quantity"], "limit_price": str(row["limit_price"])}


def _reserve_and_submit(ledger, account_id, key, request_digest, order, proposal, audit, daily_count, daily_notional):
    _ensure_running()
    row, created = ledger.reserve(account_id, key, request_digest, order, proposal,
                                  audit, daily_count, daily_notional)
    if not created:
        return _result(row, duplicate=True)
    _ensure_running()
    try:
        receipt = broker._submit_paper_limit(order["symbol"], order["side"], order["quantity"],
                                             order["limit_price"], row["client_order_id"])
    except broker.AlpacaError:
        ledger.submission(row)
        return _result({**row, "state": "unknown"})
    ledger.submission(row, receipt)
    return _result({**row, "state": "submitted", "broker_order_id": receipt["id"],
                    "broker_status": receipt["status"]})


def run(prompt: str, *, limits: RiskLimits | None = None, peak_equity: Decimal | None = None,
        execute_paper: bool = False, symbol: str | None = None, decision_key: str | None = None) -> dict:
    """Execution authorization, decision identity, and limits are outside model input."""
    if type(execute_paper) is not bool:
        raise ValueError("Execution opt-in must be a boolean")
    if not execute_paper:
        proposal = agent.generate_proposal(prompt, limits=limits or RiskLimits(), peak_equity=peak_equity)
        return {"mode": "proposal", "proposal": proposal.model_dump(mode="json")}
    _ensure_running()
    if limits is not None or peak_equity is not None:
        raise ValueError("Paper execution uses only stored database limits and peak equity")
    if not isinstance(symbol, str) or not re.fullmatch(SYMBOL, symbol):
        raise ValueError("Paper execution requires a user-selected symbol")
    if not isinstance(decision_key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", decision_key):
        raise ValueError("Paper execution requires a stable --decision-key")
    request_digest = digest({"symbol": symbol, "prompt": prompt})
    with connect() as ledger:
        if row := ledger.existing(decision_key, request_digest):
            return {"mode": "paper-execution", "order": _result(row, duplicate=True)}
        account = _paper_account()
        account_id = ledger.account(account)
        with ledger.lock(account_id):
            if row := ledger.existing(decision_key, request_digest):
                return {"mode": "paper-execution", "order": _result(row, duplicate=True)}
            limits, peak, _, _ = ledger.controls(account_id)
            ledger.record_equity(account_id, account["equity"])
            proposal = agent.generate_proposal(
                f"Paper execution is enabled for {symbol} only. Propose at most one target for {symbol}.\n{prompt}",
                limits=limits, peak_equity=max(peak, account["equity"]),
            )
            if not proposal.targets:
                return {"mode": "paper-execution", "order": None}
            if len(proposal.targets) != 1 or proposal.targets[0].symbol != symbol:
                raise ValueError("Proposal is outside the user-selected paper execution scope")
            order = _execute(proposal, ledger, account_id, account["external_account_id"], decision_key, request_digest)
    return {"mode": "paper-execution", "order": order}


def submit_paper_order(symbol: str, side: str, quantity: int, decision_key: str) -> dict:
    """Submit one user-confirmed, whole-share limit order using the audited paper controls."""
    _ensure_running()
    if not isinstance(symbol, str) or not re.fullmatch(SYMBOL, symbol):
        raise ValueError("A valid uppercase symbol is required")
    if side not in ("buy", "sell") or type(quantity) is not int or not 1 <= quantity <= 1_000_000:
        raise ValueError("Order must have a buy or sell side and 1 to 1,000,000 whole shares")
    if not isinstance(decision_key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", decision_key):
        raise ValueError("A stable paper order key is required")
    request_digest = digest({"symbol": symbol, "side": side, "quantity": quantity})
    with connect() as ledger:
        if row := ledger.existing(decision_key, request_digest):
            return {"mode": "paper-execution", "order": _result(row, duplicate=True)}
        account = _paper_account()
        account_id = ledger.account(account)
        with ledger.lock(account_id):
            if row := ledger.existing(decision_key, request_digest):
                return {"mode": "paper-execution", "order": _result(row, duplicate=True)}
            limits, peak_equity, daily_count, daily_notional = ledger.controls(account_id)
            ledger.record_equity(account_id, account["equity"])
            external_id = account["external_account_id"]
            asset = broker._get(broker.PAPER_URL, f"/v2/assets/{symbol}")
            if not isinstance(asset, dict) or asset.get("class") != "us_equity" or asset.get("tradable") is not True:
                raise ValueError("Paper orders require a tradable US stock or ETF")
            if broker.get_orders(status="open", limit=1):
                raise ValueError("An Alpaca paper order is already open")
            account = _paper_account()
            if account["external_account_id"] != external_id:
                raise ValueError("Alpaca account changed during execution")
            equity, cash = account["equity"], account["cash"]
            positions = broker.get_positions()
            if any(position["market_value"] is None or position["quantity"] < 0 for position in positions):
                raise ValueError("Paper execution requires priced long-only holdings")
            with localcontext(Context(prec=64)):
                price, quote_as_of = _reference_price(symbol)
                held = sum((position["quantity"] for position in positions if position["symbol"] == symbol), Decimal(0))
                if side == "sell" and quantity > held:
                    raise ValueError("Sell quantity exceeds the shares held; short selling is disabled")
                notional = Decimal(quantity) * price
                if side == "buy" and (cash is None or cash < notional):
                    raise ValueError("Paper order exceeds available cash")
                projected = [Position(position["symbol"], None, position["market_value"])
                             for position in positions if position["symbol"] != symbol]
                final_quantity = held + Decimal(quantity if side == "buy" else -quantity)
                if final_quantity:
                    projected.append(Position(symbol, None, final_quantity * price))
                if limits.max_sector_weight is not None:
                    sectors = portfolio_sectors.classifications(position.symbol for position in projected
                                                                  if position.market_value)
                    projected = classified_positions(projected, sectors)
                breaches = check_limits(projected, equity, max(equity, peak_equity), limits,
                                        order_notional=notional)
            if breaches:
                raise ValueError("Paper order breaches " + ", ".join(sorted({breach.limit for breach in breaches})))
            clock = broker._get(broker.PAPER_URL, "/v2/clock")
            if not isinstance(clock, dict) or clock.get("is_open") is not True:
                raise ValueError("Paper execution requires regular market hours")
            order = {"symbol": symbol, "side": side, "quantity": quantity, "limit_price": price}
            proposal = {"mode": "user-confirmed-paper-order", "symbol": symbol,
                        "side": side, "quantity": quantity, "quote_as_of": quote_as_of.isoformat()}
            audit = {"equity": equity, "cash": cash, "peak_equity": max(equity, peak_equity),
                     "limits": asdict(limits), "positions": positions,
                     "projected": [asdict(position) for position in projected],
                     "quote_as_of": quote_as_of.isoformat(), "quote_source": "Finnhub",
                     "daily_order_cap": daily_count, "daily_notional_cap": daily_notional}
            result = _reserve_and_submit(ledger, account_id, decision_key, request_digest,
                                         order, proposal, audit, daily_count, daily_notional)
            return {"mode": "paper-execution", "order": result}


def record_equity():
    with connect() as ledger:
        account = _paper_account()
        account_id = ledger.account(account)
        with ledger.lock(account_id):
            ledger.record_equity(account_id, account["equity"])
        return {"account_id": account_id, "recorded": True}


def reconcile():
    """Perform only broker reads and database writes. Safe to invoke again."""
    with connect() as ledger:
        account_id = ledger.account(_paper_account())
        with ledger.lock(account_id):
            settled = inspected = 0
            for row in ledger.pending(account_id):
                inspected += 1
                order = broker._paper_order(row["client_order_id"])
                if order is None:
                    ledger.missing(row)
                    continue
                if (order["symbol"] != row["symbol"] or order["side"] != row["side"]
                        or (row["broker_order_id"] and order["id"] != row["broker_order_id"])
                        or not 0 <= order["filled_quantity"] <= row["quantity"]):
                    raise ValueError("Broker order does not match the durable paper intent")
                fills = broker._paper_fills(order["id"]) if order["filled_quantity"] else []
                if any(f["symbol"] != row["symbol"] or f["side"] != row["side"] for f in fills):
                    raise ValueError("Broker fill does not match the durable paper intent")
                settled += ledger.reconcile(row, order, fills)
            return {"inspected": inspected, "settled": settled}


def _reference_price(symbol: str) -> tuple[Decimal, datetime]:
    quote = market_data.finnhub_quote(symbol)
    try:
        price = Decimal(str(quote["price"]))
        as_of = datetime.fromisoformat(quote["as_of"])
        now = datetime.now(timezone.utc)
        if not now - timedelta(minutes=2) <= as_of <= now + timedelta(seconds=5):
            raise ValueError("Paper order requires a fresh Finnhub quote")
        if not price.is_finite() or price < 1:
            raise ValueError("Paper execution requires a USD price of at least one dollar")
        return price.quantize(Decimal(".01")), as_of
    except (KeyError, TypeError, DecimalException):
        raise ValueError("Invalid Finnhub quote") from None


def _execute(proposal: Proposal, ledger, account_id, external_id, key, request_digest) -> dict | None:
    _ensure_running()
    limits, peak_equity, daily_count, daily_notional = ledger.controls(account_id)
    target = proposal.targets[0]
    symbol = target.symbol
    asset = broker._get(broker.PAPER_URL, f"/v2/assets/{symbol}")
    if not isinstance(asset, dict) or asset.get("class") != "us_equity" or asset.get("tradable") is not True:
        raise ValueError("Paper execution requires a tradable US equity")
    if broker.get_orders(status="open", limit=1):
        raise ValueError("An Alpaca paper order is already open")
    account = _paper_account()
    if account["external_account_id"] != external_id:
        raise ValueError("Alpaca account changed during execution")
    equity, cash = account["equity"], account["cash"]
    ledger.record_equity(account_id, equity)
    positions = broker.get_positions()
    if any(p["market_value"] is None or p["quantity"] < 0 for p in positions):
        raise ValueError("Paper execution requires priced long-only holdings")
    with localcontext(Context(prec=64)):
        price, quote_as_of = _reference_price(symbol)
        held = sum((p["quantity"] for p in positions if p["symbol"] == symbol), Decimal(0))
        # Dollar targets are converted to whole shares at the order limit.
        difference = Decimal(size_notional(equity * target.target_weight, price)) - held
        quantity = int(abs(difference))
        if not quantity:
            return None
        side = "buy" if difference > 0 else "sell"
        notional = quantity * price
        if side == "buy" and (cash is None or cash < notional):
            raise ValueError("Paper order exceeds available cash")
        projected = [Position(p["symbol"], None, p["market_value"]) for p in positions if p["symbol"] != symbol]
        final_quantity = held + (quantity if side == "buy" else -quantity)
        projected.append(Position(symbol, None, final_quantity * price))
        if limits.max_sector_weight is not None:
            sectors = portfolio_sectors.classifications(p.symbol for p in projected if p.market_value)
            projected = classified_positions(projected, sectors)
        breaches = check_limits(projected, equity, max(equity, peak_equity), limits, order_notional=notional)
    if breaches:
        raise ValueError("Paper order breaches " + ", ".join(sorted({b.limit for b in breaches})))
    clock = broker._get(broker.PAPER_URL, "/v2/clock")
    if not isinstance(clock, dict) or clock.get("is_open") is not True:
        raise ValueError("Paper execution requires regular market hours")
    order = {"symbol": symbol, "side": side, "quantity": quantity, "limit_price": price}
    audit = {"equity": equity, "cash": cash, "peak_equity": max(equity, peak_equity),
             "limits": asdict(limits), "positions": positions, "projected": [asdict(p) for p in projected],
             "quote_as_of": quote_as_of.isoformat(), "quote_source": "Finnhub",
             "daily_order_cap": daily_count, "daily_notional_cap": daily_notional}
    return _reserve_and_submit(ledger, account_id, key, request_digest, order,
                               proposal.model_dump(mode="json"), audit, daily_count, daily_notional)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?")
    parser.add_argument("--peak-equity", type=Decimal, help="Proposal mode only")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute-paper", action="store_true", help="Authorize at most one paper order for this decision")
    mode.add_argument("--record-equity", action="store_true", help="Record a trusted paper equity observation")
    mode.add_argument("--reconcile", action="store_true", help="Read broker order and fill status into the ledger")
    parser.add_argument("--symbol", help="Only symbol this run may trade")
    parser.add_argument("--decision-key", help="Stable operator-chosen key reused on every retry")
    for name in ("max-order-notional", "max-gross-notional", "max-name-weight", "max-sector-weight", "max-drawdown"):
        parser.add_argument(f"--{name}", type=Decimal, help="Proposal mode only")
    args = parser.parse_args()
    try:
        if args.record_equity:
            result = record_equity()
        elif args.reconcile:
            result = reconcile()
        else:
            if not args.prompt or (not args.execute_paper and args.peak_equity is None):
                raise ValueError("Provide a prompt and, in proposal mode, --peak-equity")
            caps = dict(max_order_notional=args.max_order_notional, max_gross_notional=args.max_gross_notional,
                        max_name_weight=args.max_name_weight, max_sector_weight=args.max_sector_weight,
                        max_drawdown=args.max_drawdown)
            limits = RiskLimits(**caps) if any(value is not None for value in caps.values()) else None
            result = run(args.prompt, limits=limits, peak_equity=args.peak_equity, execute_paper=args.execute_paper,
                         symbol=args.symbol, decision_key=args.decision_key)
    except (ValueError, DecimalException) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
