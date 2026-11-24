import os
import re
from threading import Lock
import time
from datetime import date
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
_request_lock = Lock()
_cik_cache = {}
_ticker_cache = {}
_session = requests.Session()


def _rate_limited_get(url: str, params: dict = None) -> requests.Response:
    """Execute GET request with SEC User-Agent header, rate limiting, and exponential backoff on 429."""
    global _last_request_time
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc not in {"www.sec.gov", "data.sec.gov", "efts.sec.gov"}:
        raise ValueError("Only HTTPS SEC endpoints are allowed")
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": urlparse(url).netloc,
    }

    retries = 3
    backoff = 1.0

    for attempt in range(retries):
        with _request_lock:
            elapsed = time.monotonic() - _last_request_time
            if elapsed < SEC_RATE_LIMIT_DELAY:
                time.sleep(SEC_RATE_LIMIT_DELAY - elapsed)
            _last_request_time = time.monotonic()

        resp = _session.get(url, headers=headers, params=params, timeout=15, allow_redirects=False)
        if resp.status_code == 429:
            time.sleep(backoff)
            backoff *= 2
            continue
        if 300 <= resp.status_code < 400:
            raise ValueError("SEC redirects are not allowed")
        resp.raise_for_status()
        return resp

    resp.raise_for_status()
    return resp


def tool_cik_lookup(company_name_or_ticker: str) -> str:
    """Maps a company name or ticker to its 10-digit zero-padded CIK using SEC company_tickers.json."""
    global _cik_cache
    target = company_name_or_ticker.strip().upper()
    if not target:
        return ""

    if not _cik_cache:
        url = "https://www.sec.gov/files/company_tickers.json"
        data = _rate_limited_get(url).json()
        for item in data.values():
            cik_padded = str(item["cik_str"]).zfill(10)
            _ticker_cache[item["ticker"].upper()] = cik_padded
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


def tool_full_text_search(query: str, form_type: str = "10-K", start_date: str = "", *, cik: str = "") -> list:
    """Queries efts.sec.gov to locate filing documents matching keywords and form types."""
    if not isinstance(query, str) or not query.strip() or len(query) > 2000:
        raise ValueError("Search query must contain 1 to 2000 characters")
    if not isinstance(form_type, str) or (form_type and not re.fullmatch(r"[A-Z0-9 /-]{1,32}", form_type)):
        raise ValueError("Invalid SEC form type")
    url = f"https://efts.sec.gov/LATEST/search-index?q={quote(query)}"
    params = {}
    if cik:
        params["ciks"] = _validate_cik(cik)
    if form_type:
        params["forms"] = form_type
    if start_date:
        date.fromisoformat(start_date)
        params.update({"dateRange": "custom", "startdt": start_date, "enddt": date.today().isoformat()})

    resp = _rate_limited_get(url, params=params)
    data = resp.json()
    hits = data.get("hits", {}).get("hits", [])

    results = []
    for hit in hits[:10]:
        src = hit.get("_source", {})
        ciks = src.get("ciks", [])
        hit_ciks = [str(item).zfill(10) for item in ciks]
        if cik and params["ciks"] not in hit_ciks:
            continue
        hit_cik = params["ciks"] if cik else hit_ciks[0] if hit_ciks else ""
        hit_id = hit.get("_id", "")
        file_name = hit_id.split(":", 1)[1] if ":" in hit_id else src.get("file_name", "")
        root_forms = src.get("root_forms", [])
        root_form = root_forms[0] if root_forms else src.get("root_form", "")

        results.append({
            "cik": hit_cik,
            "adsh": src.get("adsh", ""),
            "form": src.get("form", ""),
            "file_date": src.get("file_date", ""),
            "file_name": file_name,
            "root_form": root_form,
            "snippet": re.sub(r"<[^>]+>", "", hit.get("highlight", {}).get("text", [""])[0]) if hit.get("highlight") else ""
        })
    return results



def resolve_cik(ticker: str) -> str:
    """Resolve an exact ticker, rejecting company-name and partial matches."""
    ticker = ticker.strip().upper()
    tool_cik_lookup(ticker)
    if ticker not in _ticker_cache:
        raise ValueError("No company matched. Use a ticker symbol, e.g. 'NVDA'.")
    return _ticker_cache[ticker]


def _validate_cik(cik: str) -> str:
    if not isinstance(cik, str) or not re.fullmatch(r"[0-9]{1,10}", cik) or int(cik) == 0:
        raise ValueError("CIK must contain 1 to 10 digits and be nonzero")
    return cik.zfill(10)


def _validate_filename(filename: str) -> str:
    if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}", filename) or ".." in filename:
        raise ValueError("Invalid SEC filename")
    return filename


def _submission_batches(cik, since=""):
    data = _rate_limited_get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()["filings"]
    yield data["recent"]
    for entry in sorted(data.get("files", []), key=lambda item: item.get("filingTo", ""), reverse=True):
        if entry.get("filingTo") and entry["filingTo"] < since:
            continue
        filename = _validate_filename(entry["name"])
        yield _rate_limited_get(f"https://data.sec.gov/submissions/{filename}").json()


def _submission_rows(batch):
    columns = zip(batch["form"], batch["filingDate"], batch["accessionNumber"], batch["primaryDocument"], strict=True)
    report_dates = batch.get("reportDate")
    return sorted(
        ({"form": form, "filing_date": day, "accession_number": accession, "filename": filename,
          "report_date": report_dates[index] or None if report_dates else None}
         for index, (form, day, accession, filename) in enumerate(columns)),
        key=lambda filing: (filing["filing_date"], filing["accession_number"]), reverse=True,
    )


def latest_filing(cik: str, form: str = "10-K") -> dict:
    """Find the latest original filing of the requested form in SEC submissions."""
    cik = _validate_cik(cik)
    if form not in ("10-K", "10-Q"):
        raise ValueError("Form must be 10-K or 10-Q")
    for batch in _submission_batches(cik):
        for filing in _submission_rows(batch):
            if filing["form"] == form and filing["filename"]:
                return {key: filing[key] for key in ("filing_date", "accession_number", "filename")}
    raise ValueError(f"No {form} found for CIK {cik}")


def filing_timeline(cik: str, form: str = "", since: str = "", limit: int = 20) -> dict:
    """List recent and archived SEC submissions with a bounded result size."""
    cik = _validate_cik(cik)
    form = form.strip().upper()
    if form and not re.fullmatch(r"[A-Z0-9 /-]{1,32}", form):
        raise ValueError("Invalid SEC form type")
    since = date.fromisoformat(since).isoformat() if since else ""
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("Filing limit must be between 1 and 50")
    filings = []
    seen = set()
    for batch in _submission_batches(cik, since):
        for row in _submission_rows(batch):
            if (form and row["form"] != form) or row["filing_date"] < since:
                continue
            accession = _validate_accession(row["accession_number"])
            if accession in seen:
                continue
            if len(filings) == limit:
                return {"cik": cik, "filings": filings, "truncated": True}
            seen.add(accession)
            filename = row["filename"]
            # SEC ownership forms can use a stylesheet directory for their primary XML.
            directory, sep, leaf = filename.rpartition("/")
            valid_directory = not sep or bool(re.fullmatch(r"xsl[A-Za-z0-9]+", directory))
            try:
                _validate_filename(leaf)
                if not valid_directory:
                    raise ValueError("Invalid SEC directory")
            except ValueError:
                filename = ""
            base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}"
            row.update({"filename": filename, "url": f"{base}/{filename or accession + '-index.html'}"})
            filings.append(row)
    return {"cik": cik, "filings": filings, "truncated": False}


def latest_10k(cik: str) -> dict:
    return latest_filing(cik, "10-K")

def _validate_accession(accession_number: str) -> str:
    if not isinstance(accession_number, str) or not re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", accession_number):
        raise ValueError("Invalid SEC accession number")
    return accession_number


def tool_fetch_filing_text(cik: str, accession_number: str, filename: str) -> str:
    """Reconstructs the SEC archive URL and downloads the raw text/HTML of the filing."""
    clean_cik = str(int(_validate_cik(cik)))
    clean_adsh = _validate_accession(accession_number).replace("-", "")
    filename = _validate_filename(filename)
    url = f"https://www.sec.gov/Archives/edgar/data/{clean_cik}/{clean_adsh}/{filename}"
    resp = _rate_limited_get(url)
    return resp.text


def company_facts(cik: str, **json_options) -> dict:
    padded_cik = _validate_cik(cik)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
    return _rate_limited_get(url).json(**json_options)


def tool_get_financial_facts(cik: str, concept: str) -> dict:
    """Pulls specific numeric XBRL facts (e.g., Revenues, NetIncomeLoss) for a CIK."""
    if not isinstance(concept, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,199}", concept):
        raise ValueError("Invalid financial concept")
    data = company_facts(cik)

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
