import os
import re
import time
from urllib.parse import urlparse, quote
import requests

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except ImportError:
    pass

# SEC strictly requires User-Agent in format: Sample Company Name AdminContact@<domain>.com
DEFAULT_USER_AGENT = os.getenv("SEC_USER_AGENT", "TheMonroeFund research@themonroefund.com")
SEC_RATE_LIMIT_DELAY = 0.11  # At least 110ms between calls to enforce <= 10 req/sec

_last_request_time = 0.0
_cik_cache = {}
_session = requests.Session()


def _rate_limited_get(url: str, params: dict = None) -> requests.Response:
    """Execute GET request with SEC User-Agent header, rate limiting, and exponential backoff on 429."""
    global _last_request_time
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": urlparse(url).netloc,
    }

    retries = 3
    backoff = 1.0

    for attempt in range(retries):
        elapsed = time.time() - _last_request_time
        if elapsed < SEC_RATE_LIMIT_DELAY:
            time.sleep(SEC_RATE_LIMIT_DELAY - elapsed)
        _last_request_time = time.time()

        resp = _session.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 429:
            time.sleep(backoff)
            backoff *= 2
            continue
        resp.raise_for_status()
        return resp

    resp.raise_for_status()
    return resp


def tool_cik_lookup(company_name_or_ticker: str) -> str:
    """Maps a company name or ticker to its 10-digit zero-padded CIK using SEC company_tickers.json."""
    global _cik_cache
    target = company_name_or_ticker.strip().upper()

    if not _cik_cache:
        url = "https://www.sec.gov/files/company_tickers.json"
        data = _rate_limited_get(url).json()
        for item in data.values():
            cik_padded = str(item["cik_str"]).zfill(10)
            _cik_cache[item["ticker"].upper()] = cik_padded
            _cik_cache[item["title"].upper()] = cik_padded

    # Direct match by ticker or company name
    if target in _cik_cache:
        return _cik_cache[target]

    # Partial match on title if not exact
    for name, cik in _cik_cache.items():
        if target in name:
            return cik

    # shortcut: simple substring fallback without fuzzy matching, upgrade to rapidfuzz when typo tolerance is needed
    return ""


def tool_full_text_search(query: str, form_type: str = "10-K", start_date: str = "") -> list:
    """Queries efts.sec.gov to locate filing documents matching keywords and form types."""
    url = f"https://efts.sec.gov/LATEST/search-index?q={quote(query)}"
    params = {}
    if form_type:
        params["forms"] = form_type
    if start_date:
        params["startdt"] = start_date

    resp = _rate_limited_get(url, params=params)
    data = resp.json()
    hits = data.get("hits", {}).get("hits", [])

    results = []
    for hit in hits[:10]:
        src = hit.get("_source", {})
        ciks = src.get("ciks", [])
        cik = str(ciks[0]).zfill(10) if ciks else ""
        hit_id = hit.get("_id", "")
        file_name = hit_id.split(":", 1)[1] if ":" in hit_id else src.get("file_name", "")
        root_forms = src.get("root_forms", [])
        root_form = root_forms[0] if root_forms else src.get("root_form", "")

        results.append({
            "cik": cik,
            "adsh": src.get("adsh", ""),
            "form": src.get("form", ""),
            "file_date": src.get("file_date", ""),
            "file_name": file_name,
            "root_form": root_form,
            "snippet": re.sub(r"<[^>]+>", "", hit.get("highlight", {}).get("text", [""])[0]) if hit.get("highlight") else ""
        })
    return results


def tool_fetch_filing_text(cik: str, accession_number: str, filename: str) -> str:
    """Reconstructs the SEC archive URL and downloads the raw text/HTML of the filing."""
    clean_cik = str(cik).lstrip("0")
    clean_adsh = accession_number.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{clean_cik}/{clean_adsh}/{filename}"
    resp = _rate_limited_get(url)
    return resp.text


def tool_get_financial_facts(cik: str, concept: str) -> dict:
    """Pulls specific numeric XBRL facts (e.g., Revenues, NetIncomeLoss) for a CIK."""
    padded_cik = str(cik).zfill(10)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
    data = _rate_limited_get(url).json()

    facts = data.get("facts", {})
    # Search us-gaap first, then ifrs-full
    for taxonomy in ["us-gaap", "dei", "ifrs-full"]:
        if taxonomy in facts and concept in facts[taxonomy]:
            item = facts[taxonomy][concept]
            units = item.get("units", {})
            return {
                "label": item.get("label", concept),
                "description": item.get("description", ""),
                "units": {k: v[-5:] for k, v in units.items()}  # Last 5 recent reporting periods
            }

    # shortcut: returns empty dict on unindexed concepts, upgrade to full taxonomy search when needed
    return {}
