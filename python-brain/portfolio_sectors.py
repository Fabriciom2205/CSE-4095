"""Classify issuers into the official SIC divisions using EDGAR issuer metadata."""

from datetime import datetime, timezone
from functools import lru_cache

from requests import RequestException

import sec_client

# The SEC's SIC codes use the two-digit major groups in the SIC manual.
DIVISIONS = (
    (range(1, 10), "agriculture, forestry and fishing"),
    (range(10, 15), "mining"),
    (range(15, 18), "construction"),
    (range(20, 40), "manufacturing"),
    (range(40, 50), "transportation, communications and utilities"),
    (range(50, 52), "wholesale trade"),
    (range(52, 60), "retail trade"),
    (range(60, 68), "finance, insurance and real estate"),
    (range(70, 90), "services"),
    (range(91, 98), "public administration"),
)
# EDGAR uses these values for registrations without a useful operating industry.
UNCLASSIFIED = {"6189", "6770", "8880", "8888", "9995"}


@lru_cache(maxsize=512)
def _sector(symbol, utc_day):
    try:
        cik = sec_client.resolve_cik(symbol)
        record = sec_client.company_submissions(cik)
        if not isinstance(record, dict):
            raise ValueError("Invalid EDGAR issuer metadata")
        sic = str(record.get("sic", ""))
        if (str(record.get("cik")).zfill(10) == cik and sic not in UNCLASSIFIED
                and sic.isascii() and sic.isdigit() and len(sic) in (3, 4)):
            for groups, label in DIVISIONS:
                if int(sic) // 100 in groups:
                    return label
    except (ValueError, RequestException):
        pass
    raise ValueError(f"Sector cap requires an EDGAR SIC classification for {symbol}")


def classifications(symbols):
    """Get current sectors. Failed lookups are retried on subsequent requests."""
    utc_day = datetime.now(timezone.utc).date()
    return {symbol: _sector(symbol, utc_day) for symbol in sorted(set(symbols))}
