"""Massive and Finnhub market data clients.

Massive (formerly Polygon.io) supplies daily price bars and ticker reference data.
Finnhub supplies quotes, company news, basic financial metrics, and earnings dates.
Keys come from MASSIVE_API_KEY and FINNHUB_API_KEY and travel in request headers,
never in URLs, so they stay out of logs and error messages.
"""

import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote, urlparse

import requests

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except ImportError:
    pass

MASSIVE_URL = "https://api.massive.com"
FINNHUB_URL = "https://finnhub.io/api/v1"
MAX_RANGE_DAYS = 366
MAX_NEWS_DAYS = 31
MAX_NEWS_ITEMS = 20
MAX_SUMMARY_CHARS = 500
RETRIES = 3

# provider -> (display name, API key variable, allowed host)
PROVIDERS = {
    "massive": ("Massive", "MASSIVE_API_KEY", "api.massive.com"),
    "finnhub": ("Finnhub", "FINNHUB_API_KEY", "finnhub.io"),
}
_SYMBOL = re.compile(r"[A-Z][A-Z0-9.-]{0,9}")
_session = requests.Session()


def api_key(provider: str) -> str:
    """Returns the configured key, or an empty string when unset or still the .env.example placeholder."""
    key = os.getenv(PROVIDERS[provider][1], "").strip()
    return "" if key.startswith("your_") else key


def _get(provider: str, url: str, params: dict | None = None):
    """GET a provider endpoint with header authentication, retrying briefly on rate limits."""
    name, env_name, host = PROVIDERS[provider]
    key = api_key(provider)
    if not key:
        raise ValueError(f"{env_name} is not configured; add it to the repository .env file.")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != host:
        raise ValueError(f"Only HTTPS {name} endpoints are allowed")
    headers = {"Authorization": f"Bearer {key}"} if provider == "massive" else {"X-Finnhub-Token": key}

    for attempt in range(RETRIES):
        try:
            # Redirects could forward the key header to another host
            resp = _session.get(url, params=params, headers=headers, timeout=15, allow_redirects=False)
        except requests.RequestException as error:
            raise ValueError(f"{name} request failed: {type(error).__name__}") from error
        if resp.status_code != 429 or attempt == RETRIES - 1:
            break
        time.sleep(2 ** attempt)

    status = resp.status_code
    if status == 429:
        raise ValueError(f"{name} rate limit reached; wait a minute or check the plan's request limit.")
    if status in (401, 403):
        raise ValueError(f"{name} rejected the request (HTTP {status}); check {env_name} and whether the plan includes this data.")
    if status == 404:
        raise ValueError(f"{name} has no data for this request (HTTP 404)")
    if 300 <= status < 400:
        raise ValueError(f"{name} redirects are not allowed")
    if status >= 400:
        raise ValueError(f"{name} request failed (HTTP {status})")
    try:
        return resp.json()
    except ValueError:
        raise ValueError(f"{name} returned a response that is not JSON") from None


def _symbol(value: str) -> str:
    symbol = str(value).strip().upper()
    if not _SYMBOL.fullmatch(symbol):
        raise ValueError("Ticker must be 1 to 10 characters, e.g. 'AAPL' or 'BRK.B'")
    return symbol


def _day(value: str, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"Dates must use YYYY-MM-DD, got {value!r}") from None


def _date_range(start_date: str, end_date: str, default_start: date, default_end: date, max_days: int) -> tuple[str, str]:
    start, end = _day(start_date, default_start), _day(end_date, default_end)
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    if (end - start).days > max_days:
        raise ValueError(f"Date range must span at most {max_days} days; split it into smaller requests")
    return start.isoformat(), end.isoformat()


def _utc(seconds: float) -> datetime:
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _bar(bar: dict) -> dict:
    # Massive timestamps are Unix milliseconds at the start of the trading day (US Eastern midnight)
    return {"date": _utc(bar["t"] / 1000).date().isoformat(), "open": bar.get("o"), "high": bar.get("h"),
            "low": bar.get("l"), "close": bar.get("c"), "volume": bar.get("v"), "vwap": bar.get("vw")}


# ------------------------------------------------------------------------------
# Massive
# ------------------------------------------------------------------------------

TICKER_FIELDS = ("name", "market", "primary_exchange", "type", "active", "currency_name", "cik", "market_cap",
                 "share_class_shares_outstanding", "weighted_shares_outstanding", "sic_description",
                 "total_employees", "list_date", "homepage_url", "description")


def massive_daily_bars(ticker: str, start_date: str = "", end_date: str = "", *, adjusted: bool = True) -> dict:
    symbol = _symbol(ticker)
    today = date.today()
    start, end = _date_range(start_date, end_date, today - timedelta(days=30), today, MAX_RANGE_DAYS)
    data = _get("massive", f"{MASSIVE_URL}/v2/aggs/ticker/{quote(symbol)}/range/1/day/{start}/{end}",
                {"adjusted": "true" if adjusted else "false", "sort": "asc", "limit": 5000})
    if data.get("next_url"):
        raise ValueError(f"Massive returned an incomplete bar window for {symbol}")
    bars = [_bar(bar) for bar in data.get("results") or []]
    return {"ticker": symbol, "start_date": start, "end_date": end, "adjusted": adjusted, "bars": bars}


def massive_splits(ticker: str, start_date: str, end_date: str) -> list:
    symbol = _symbol(ticker)
    start, end = _date_range(start_date, end_date, date.today(), date.today(), MAX_RANGE_DAYS)
    data = _get("massive", f"{MASSIVE_URL}/stocks/v1/splits",
                {"ticker": symbol, "execution_date.gte": start, "execution_date.lte": end, "limit": 100})
    if data.get("next_url"):
        raise ValueError(f"Massive returned an incomplete split window for {symbol}")
    splits = data.get("results", [])
    if not isinstance(splits, list):
        raise ValueError("Massive returned an unexpected split response")
    return splits


def massive_previous_close(ticker: str) -> dict:
    symbol = _symbol(ticker)
    data = _get("massive", f"{MASSIVE_URL}/v2/aggs/ticker/{quote(symbol)}/prev", {"adjusted": "true"})
    results = data.get("results") or []
    if not results:
        raise ValueError(f"Massive has no previous close for {symbol}")
    return {"ticker": symbol, "adjusted": True, **_bar(results[0])}


def massive_ticker_details(ticker: str) -> dict:
    symbol = _symbol(ticker)
    details = _get("massive", f"{MASSIVE_URL}/v3/reference/tickers/{quote(symbol)}").get("results") or {}
    if not details:
        raise ValueError(f"Massive has no details for {symbol}")
    return {"ticker": symbol, **{k: details[k] for k in TICKER_FIELDS if details.get(k) is not None}}


# ------------------------------------------------------------------------------
# Finnhub
# ------------------------------------------------------------------------------

EARNINGS_FIELDS = {"date": "date", "hour": "hour", "quarter": "quarter", "year": "year",
                   "eps_estimate": "epsEstimate", "eps_actual": "epsActual",
                   "revenue_estimate": "revenueEstimate", "revenue_actual": "revenueActual"}


def finnhub_quote(symbol: str) -> dict:
    symbol = _symbol(symbol)
    data = _get("finnhub", f"{FINNHUB_URL}/quote", {"symbol": symbol})
    # Finnhub answers unknown symbols with HTTP 200 and all-zero fields
    if not data.get("t"):
        raise ValueError(f"Finnhub has no quote for {symbol}")
    return {"symbol": symbol, "price": data.get("c"), "change": data.get("d"), "percent_change": data.get("dp"),
            "open": data.get("o"), "high": data.get("h"), "low": data.get("l"),
            "previous_close": data.get("pc"), "as_of": _utc(data["t"]).isoformat()}


def finnhub_company_news(symbol: str, start_date: str = "", end_date: str = "") -> dict:
    symbol = _symbol(symbol)
    today = date.today()
    start, end = _date_range(start_date, end_date, today - timedelta(days=7), today, MAX_NEWS_DAYS)
    items = _get("finnhub", f"{FINNHUB_URL}/company-news", {"symbol": symbol, "from": start, "to": end})
    if not isinstance(items, list):
        raise ValueError("Finnhub returned an unexpected news response")
    items.sort(key=lambda item: item.get("datetime") or 0, reverse=True)
    articles = [{
        "published": _utc(item["datetime"]).isoformat() if item.get("datetime") else None,
        "headline": item.get("headline"),
        "source": item.get("source"),
        "summary": (item.get("summary") or "")[:MAX_SUMMARY_CHARS],
        "url": item.get("url"),
    } for item in items[:MAX_NEWS_ITEMS]]
    return {"symbol": symbol, "start_date": start, "end_date": end, "total_articles": len(items), "articles": articles}


def finnhub_basic_financials(symbol: str) -> dict:
    symbol = _symbol(symbol)
    metrics = _get("finnhub", f"{FINNHUB_URL}/stock/metric", {"symbol": symbol, "metric": "all"}).get("metric") or {}
    if not metrics:
        raise ValueError(f"Finnhub has no financial metrics for {symbol}")
    return {"symbol": symbol, "metrics": metrics}


def finnhub_earnings_calendar(symbol: str, start_date: str = "", end_date: str = "") -> dict:
    symbol = _symbol(symbol)
    today = date.today()
    start, end = _date_range(start_date, end_date, today - timedelta(days=90), today + timedelta(days=90), MAX_RANGE_DAYS)
    data = _get("finnhub", f"{FINNHUB_URL}/calendar/earnings", {"symbol": symbol, "from": start, "to": end})
    events = [{ours: event.get(theirs) for ours, theirs in EARNINGS_FIELDS.items()}
              for event in data.get("earningsCalendar") or []]
    events.sort(key=lambda event: event["date"] or "")
    return {"symbol": symbol, "start_date": start, "end_date": end, "earnings": events}
