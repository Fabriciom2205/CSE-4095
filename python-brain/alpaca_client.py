"""Alpaca account reads and paper-only order transport.

Financial values and quantities use Decimal. Keep brokerage responses inside the
portfolio backend because they contain private account and position data.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
import os

from dotenv import find_dotenv, load_dotenv
import requests

load_dotenv(find_dotenv())

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"
_ENVIRONMENTS = {PAPER_URL: "paper", LIVE_URL: "live"}
_session = requests.Session()


class AlpacaError(ValueError):
    """A brokerage request or response failed without exposing private data."""


def _base_url() -> str:
    url = os.getenv("ALPACA_BASE_URL", PAPER_URL).strip().rstrip("/").removesuffix("/v2")
    if url not in _ENVIRONMENTS:
        raise AlpacaError("ALPACA_BASE_URL must be Alpaca's official HTTPS paper or live Trading API root")
    return url


def _credentials() -> tuple[str, str] | None:
    key = os.getenv("ALPACA_API_KEY_ID", "").strip()
    secret = os.getenv("ALPACA_API_SECRET_KEY", "").strip()
    if any(not value or value.lower().startswith("your_") for value in (key, secret)):
        return None
    return key, secret


def credentials_configured() -> bool:
    """Whether both header credentials are configured and not placeholders."""
    return _credentials() is not None


def _get(base_url: str, path: str, *, params: dict | None = None, missing_ok: bool = False) -> dict | list | None:
    credentials = _credentials()
    if credentials is None:
        raise AlpacaError("Configure ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY")
    key, secret = credentials
    try:
        response = _session.get(
            base_url + path,
            params=params,
            headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
            timeout=15,
            allow_redirects=False,
        )
    except requests.RequestException:
        raise AlpacaError("Alpaca request failed") from None

    status = response.status_code
    if 300 <= status < 400:
        raise AlpacaError("Alpaca redirects are not allowed")
    if status in (401, 403):
        raise AlpacaError(f"Alpaca rejected the credentials (HTTP {status}); check that they match the configured environment")
    if status == 404 and missing_ok:
        return None
    if status == 429:
        raise AlpacaError("Alpaca rate limit reached (HTTP 429)")
    if not 200 <= status < 300:
        raise AlpacaError(f"Alpaca request failed (HTTP {status})")
    try:
        return response.json(parse_float=Decimal)
    except ValueError:
        raise AlpacaError("Alpaca returned invalid JSON") from None


def _text(record: dict, field: str, *, nullable: bool = False) -> str | None:
    value = record.get(field)
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AlpacaError(f"Alpaca response has an invalid {field} field")
    return value


def _decimal(record: dict, field: str, *, nullable: bool = False) -> Decimal | None:
    value = record.get(field)
    if value is None and nullable:
        return None
    try:
        if type(value) not in (str, int, Decimal):
            raise InvalidOperation
        result = Decimal(value)
        if not result.is_finite():
            raise InvalidOperation
    except InvalidOperation:
        raise AlpacaError(f"Alpaca response has an invalid {field} field") from None
    return result


def _rows(data) -> list[dict]:
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise AlpacaError("Alpaca returned an invalid collection")
    return data


def get_account() -> dict:
    """Return the single Trading API account associated with the configured credentials."""
    base_url = _base_url()
    row = _get(base_url, "/v2/account")
    if not isinstance(row, dict):
        raise AlpacaError("Alpaca returned an invalid account")
    return {
        "provider": "alpaca",
        "environment": _ENVIRONMENTS[base_url],
        "external_account_id": _text(row, "id"),
        "status": _text(row, "status"),
        "currency": _text(row, "currency", nullable=True),
        "equity": _decimal(row, "equity", nullable=True),
        "cash": _decimal(row, "cash", nullable=True),
        "buying_power": _decimal(row, "buying_power", nullable=True),
    }


def get_positions() -> list[dict]:
    """Return open positions in the broker's reporting units, with signed exposure."""
    rows = _rows(_get(_base_url(), "/v2/positions"))
    positions = []
    for row in rows:
        side = _text(row, "side")
        if side not in ("long", "short"):
            raise AlpacaError("Alpaca response has an invalid side field")
        quantity = _decimal(row, "qty")
        market_value = _decimal(row, "market_value", nullable=True)
        if side == "short":
            quantity = quantity.copy_abs().copy_negate()
            if market_value is not None:
                market_value = market_value.copy_abs().copy_negate()
        elif quantity <= 0 or (market_value is not None and market_value < 0):
            raise AlpacaError("Alpaca response has invalid long exposure")
        if not quantity:
            raise AlpacaError("Alpaca returned a zero quantity for an open position")
        positions.append({
            "asset_id": _text(row, "asset_id"),
            "asset_class": _text(row, "asset_class"),
            "symbol": _text(row, "symbol"),
            "side": side,
            "quantity": quantity,
            "market_value": market_value,
            "cost_basis": _decimal(row, "cost_basis"),
            "unrealized_pl": _decimal(row, "unrealized_pl", nullable=True),
        })
    return positions


def get_orders(status: str = "all", limit: int = 50) -> list[dict]:
    """Get the newest order records in one page. Orders are not execution fills."""
    if status not in ("open", "closed", "all"):
        raise ValueError("Alpaca order status must be open, closed, or all")
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("Alpaca order limit must be between 1 and 500")
    rows = _rows(_get(_base_url(), "/v2/orders", params={"status": status, "limit": limit, "direction": "desc"}))
    return [
        {
            "external_order_id": _text(row, "id"),
            "symbol": row.get("symbol"),
            "side": row.get("side"),
            "type": _text(row, "type", nullable=True) or _text(row, "order_type", nullable=True),
            "status": _text(row, "status"),
            "quantity": _decimal(row, "qty", nullable=True),
            "notional": _decimal(row, "notional", nullable=True),
            "filled_quantity": _decimal(row, "filled_qty", nullable=True),
            "filled_avg_price": _decimal(row, "filled_avg_price", nullable=True),
            "submitted_at": row.get("submitted_at"),
            "filled_at": row.get("filled_at"),
        }
        for row in rows
    ]


def _submit_paper_limit(symbol: str, side: str, quantity: int, price: Decimal, client_order_id: str) -> dict:
    """Paper-only transport for the execution runner. Never retry a submission."""
    if _base_url() != PAPER_URL:
        raise AlpacaError("Execution requires the Alpaca paper endpoint")
    credentials = _credentials()
    if credentials is None:
        raise AlpacaError("Configure Alpaca paper credentials")
    key, secret = credentials
    payload = {
        "symbol": symbol, "side": side, "qty": str(quantity), "type": "limit",
        "time_in_force": "day", "limit_price": str(price), "client_order_id": client_order_id,
        "position_intent": "buy_to_open" if side == "buy" else "sell_to_close",
    }
    try:
        response = _session.post(
            f"{PAPER_URL}/v2/orders", json=payload, timeout=15, allow_redirects=False,
            headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret},
        )
        if 200 <= response.status_code < 300:
            row = response.json()
            if isinstance(row, dict) and row.get("client_order_id") == client_order_id and row.get("id") and row.get("status"):
                return {"id": row["id"], "status": row["status"], "client_order_id": client_order_id}
    except (requests.RequestException, ValueError):
        pass
    raise AlpacaError(f"Paper order not confirmed. Check Alpaca for client order ID {client_order_id} before retrying")


def _paper_order(client_order_id):
    """Return broker state for the persisted client ID, or None on a confirmed 404."""
    row = _get(PAPER_URL, "/v2/orders:by_client_order_id",
               params={"client_order_id": client_order_id}, missing_ok=True)
    if row is None:
        return None
    if not isinstance(row, dict) or row.get("client_order_id") != client_order_id:
        raise AlpacaError("Alpaca returned a mismatched paper order")
    return {"id": _text(row, "id"), "status": _text(row, "status"), "symbol": _text(row, "symbol"),
            "side": _text(row, "side"), "filled_quantity": _decimal(row, "filled_qty")}


def _paper_fills(order_id):
    """Fetch individual executions, including partial fills."""
    params = {"order_id": order_id, "page_size": 100, "direction": "asc"}
    seen = set()
    fills = []
    for _ in range(20):
        rows = _rows(_get(PAPER_URL, "/v2/account/activities/FILL", params=params))
        for row in rows:
            if row.get("order_id") != order_id:
                continue
            executed = datetime.fromisoformat(_text(row, "transaction_time"))
            if executed.tzinfo is None:
                raise AlpacaError("Alpaca returned an ambiguous fill timestamp")
            fills.append({"id": _text(row, "id"), "symbol": _text(row, "symbol"),
                          "side": _text(row, "side"), "quantity": _decimal(row, "qty"),
                          "price": _decimal(row, "price"), "executed_at": executed})
        if len(rows) < 100:
            return fills
        cursor = _text(rows[-1], "id")
        if cursor in seen:
            break
        seen.add(cursor)
        params["page_token"] = cursor
    raise AlpacaError("Alpaca fill pagination did not complete")
