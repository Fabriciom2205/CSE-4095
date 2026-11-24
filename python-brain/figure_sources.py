"""Research-only SEC disclosures for individual reporters and investment managers."""

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
import re
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

import sec_client

# Resolve names to an explicit filer, especially when a person is shorthand for a manager.
FIGURES = {
    "form4": {
        "jeff bezos": ("Jeffrey P. Bezos", "0001043298"),
        "warren buffett": ("Warren E. Buffett", "0000315090"),
    },
    "13f": {
        "warren buffett": ("Berkshire Hathaway Inc.", "0001067983"),
        "berkshire hathaway": ("Berkshire Hathaway Inc.", "0001067983"),
        "bill ackman": ("Pershing Square Inc.", "0002026053"),
        "pershing square": ("Pershing Square Inc.", "0002026053"),
    },
}
TRANSACTION_CODES = {"P": "purchase", "S": "sale", "G": "gift", "A": "grant_or_award",
                     "M": "exercise_or_conversion", "F": "withholding_or_payment"}


def _filer(figure, kind):
    if kind not in FIGURES:
        raise ValueError("Disclosure kind must be form4 or 13f")
    name = " ".join(figure.casefold().split())
    if name == "warren buffet":
        name = "warren buffett"
    if name in FIGURES[kind]:
        return FIGURES[kind][name]
    if re.fullmatch(r"[0-9]{1,10}", name):
        cik = sec_client._validate_cik(name)
        return f"CIK {cik}", cik
    raise ValueError("Unknown figure for this disclosure type. Use a supported name or exact SEC CIK.")


def _xml(cik, filing, filename, root_tag):
    if not filename.lower().endswith(".xml"):
        raise ValueError("Expected an EDGAR XML document")
    text = sec_client.tool_fetch_filing_text(cik, filing["accession_number"], filename)
    if len(text) > 8_000_000 or "<!DOCTYPE" in text.upper():
        raise ValueError("Unsupported EDGAR XML document")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ValueError("Invalid EDGAR XML document") from None
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    if root.tag != root_tag:
        raise ValueError("Unexpected EDGAR document type")
    return root


def _text(node, path):
    return (node.findtext(path) or "").strip() or None


def _source(filing):
    return {key: filing[key] for key in ("accession_number", "form", "filing_date", "report_date", "url")}


def _filings(cik, forms, days, limit):
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = []
    truncated = False
    for form in forms:
        page = sec_client.filing_timeline(cik, form=form, since=since, limit=limit)
        rows.extend(page["filings"])
        truncated |= page["truncated"]
    rows.sort(key=lambda x: (x["filing_date"], x["accession_number"]), reverse=True)
    return rows, truncated


def _transactions(cik, limit):
    filings, truncated = _filings(cik, ("4", "4/A"), 365, 8)
    transactions = []
    for filing in filings[:8]:
        filename = PurePosixPath(filing["filename"]).name
        root = _xml(cik, filing, filename, "ownershipDocument")
        owners = [{"cik": _text(owner, "rptOwnerCik"), "name": _text(owner, "rptOwnerName")}
                  for owner in root.findall("./reportingOwner/reportingOwnerId")]
        if not any(owner["cik"] and owner["cik"].zfill(10) == cik for owner in owners):
            continue
        for table, tag, derivative in (("nonDerivativeTable", "nonDerivativeTransaction", False),
                                       ("derivativeTable", "derivativeTransaction", True)):
            for row in root.findall(f"./{table}/{tag}"):
                code = _text(row, "transactionCoding/transactionCode")
                transaction_date = _text(row, "transactionDate/value")
                transactions.append({
                    "issuer": _text(root, "./issuer/issuerName"),
                    "symbol": _text(root, "./issuer/issuerTradingSymbol"),
                    "reporting_owners": owners,
                    "transaction_date": transaction_date,
                    "security": _text(row, "securityTitle/value"),
                    "derivative": derivative,
                    "underlying_security": _text(row, "underlyingSecurity/underlyingSecurityTitle/value"),
                    "underlying_shares": _text(row, "underlyingSecurity/underlyingSecurityShares/value"),
                    "code": code,
                    "transaction_type": TRANSACTION_CODES.get(code, "other_or_unspecified"),
                    "disposition": _text(row, "transactionAmounts/transactionAcquiredDisposedCode/value"),
                    "shares": _text(row, "transactionAmounts/transactionShares/value"),
                    "price_per_share": _text(row, "transactionAmounts/transactionPricePerShare/value"),
                    "ownership": _text(row, "ownershipNature/directOrIndirectOwnership/value"),
                    "source": _source(filing),
                })
    transactions.sort(key=lambda row: (row["source"]["filing_date"], row["transaction_date"] or ""), reverse=True)
    return {"transactions": transactions[:limit],
            "truncated": truncated or len(filings) > 8 or len(transactions) > limit,
            "coverage": "Up to eight filings from the past year. Original and amended filings are shown as filed."}


def _table_filename(cik, filing):
    accession = filing["accession_number"]
    html = sec_client.tool_fetch_filing_text(cik, accession, f"{accession}-index.htm")
    files = set()
    for row in BeautifulSoup(html, "html.parser").select("tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 4 or cells[3].get_text(strip=True) != "INFORMATION TABLE":
            continue
        for link in cells[2].find_all("a"):
            name = link.get_text(strip=True)
            if name.lower().endswith(".xml"):
                files.add(sec_client._validate_filename(name))
    if len(files) != 1:
        raise ValueError("Could not identify a unique 13F holdings XML table")
    return files.pop()


def _positions(cik, filing):
    root = _xml(cik, filing, _table_filename(cik, filing), "informationTable")
    positions = {}
    for row in root.findall("infoTable"):
        cusip = _text(row, "cusip")
        unit = _text(row, "shrsOrPrnAmt/sshPrnamtType")
        security_class = _text(row, "titleOfClass")
        option = _text(row, "putCall")
        try:
            quantity = int(_text(row, "shrsOrPrnAmt/sshPrnamt") or "")
            value = Decimal(_text(row, "value") or "")
            if not cusip or not unit or quantity < 0 or not value.is_finite() or value < 0:
                raise ValueError()
        except (ValueError, InvalidOperation):
            raise ValueError("Invalid quantity, value or security identity in SEC holdings table") from None
        key = (cusip, security_class, unit, option)
        old = positions.get(key)
        positions[key] = (_text(row, "nameOfIssuer"), quantity + (old[1] if old else 0), value + (old[2] if old else 0))
    return positions


def _snapshot(cik, filings):
    positions, sources = {}, []
    for filing in sorted(filings, key=lambda row: (row["filing_date"], row["accession_number"])):
        patch = _positions(cik, filing)
        if filing["form"] == "13F-HR/A":
            root = _xml(cik, filing, PurePosixPath(filing["filename"]).name, "edgarSubmission")
            amendment = _text(root, "./formData/coverPage/amendmentInfo/amendmentType")
            if amendment == "NEW HOLDINGS":
                for key, (issuer, quantity, value) in patch.items():
                    old = positions.get(key)
                    positions[key] = (issuer, quantity + (old[1] if old else 0), value + (old[2] if old else 0))
                sources.append(_source(filing))
                continue
            if amendment != "RESTATEMENT":
                raise ValueError("Unsupported 13F amendment type")
        positions, sources = patch, [_source(filing)]
    return positions, sources


def _holdings_changes(cik, limit):
    filings, truncated = _filings(cik, ("13F-HR", "13F-HR/A"), 730, 16)
    if truncated:
        raise ValueError("Too many 13F filings to verify complete quarter comparisons")
    periods = sorted({r["report_date"] for r in filings if r["report_date"] and r["form"] == "13F-HR"}, reverse=True)
    if len(periods) < 2:
        raise ValueError("Two 13F holdings reports are required for this manager")
    latest, previous = periods[:2]
    if not 80 <= (date.fromisoformat(latest) - date.fromisoformat(previous)).days <= 100:
        raise ValueError("Two consecutive 13F holdings quarters are required")
    old, old_sources = _snapshot(cik, [r for r in filings if r["report_date"] == previous])
    new, new_sources = _snapshot(cik, [r for r in filings if r["report_date"] == latest])
    ranked = []
    for key in sorted(old.keys() | new.keys(), key=lambda k: tuple(p or "" for p in k)):
        before, after = old.get(key), new.get(key)
        n0, n1 = before[1] if before else 0, after[1] if after else 0
        if n0 == n1:
            continue
        cusip, security_class, unit, option = key
        ranked.append((max(before[2] if before else 0, after[2] if after else 0), {
            "issuer": (after or before)[0], "cusip": cusip, "security_class": security_class,
            "unit": unit, "option": option, "previous_amount": n0, "current_amount": n1,
            "change": "new" if not n0 else "removed" if not n1 else "increased" if n1 > n0 else "decreased",
        }))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return {"current_quarter": latest, "previous_quarter": previous, "sources": new_sources + old_sources,
            "holdings_changes": [row for _, row in ranked[:limit]], "truncated": len(ranked) > limit,
            "coverage": "Changes in reported quarter-end holdings. Splits or reporting changes can affect amounts."}


def lookup(figure: str, kind: str, limit: int = 10) -> dict:
    """Find a mapped SEC filer or exact CIK and return bounded, sourced disclosures."""
    filer, cik = _filer(figure, kind)
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("Disclosure limit must be between 1 and 20")
    result = _transactions(cik, limit) if kind == "form4" else _holdings_changes(cik, limit)
    return {"filer": filer, "cik": cik, "kind": kind, **result}
