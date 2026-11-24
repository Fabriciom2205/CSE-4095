"""Deterministic navigation of SEC filings with linked tables of contents."""

from datetime import date
from difflib import unified_diff
import re

from bs4 import BeautifulSoup, Comment, NavigableString

import sec_client

MAX_EXCERPT = 12_000
SELECTORS = {"10-K": {"item 1", "item 1a", "item 7", "item 7a", "item 8"},
             "10-Q": {"part i", "part ii"}}
_HEADING = re.compile(r"^(item\s+\d{1,2}[a-z]?|part\s+(?:iv|iii|ii|i)|signatures)\b[.\s:–—-]*", re.I)
_PAGE_FOOTER = re.compile(r".*\|\s*(?:Q[1-4]\s+)?\d{4}\s+Form 10-[KQ]\s*\|\s*\d+", re.I)
_BLOCKS = {"div", "p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"}


def _section_blocks(html, selector):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script, style, noscript, header, footer, [hidden], ix\\:header"):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none\b", re.I)):
        if tag.parent is not None:
            tag.decompose()

    nodes = list(soup.descendants)
    anchors = {}
    for i, node in enumerate(nodes):
        if not isinstance(node, NavigableString):
            for attribute in ("id", "name"):
                if node.get(attribute):
                    anchors.setdefault(node[attribute], i)

    boundaries = {}
    for i, node in enumerate(nodes):
        if isinstance(node, NavigableString) or node.name != "a":
            continue
        href = node.get("href", "")
        if not href.startswith("#"):
            continue
        label = " ".join(node.stripped_strings)
        match = _HEADING.match(label)
        if match:
            target = anchors.get(href[1:])
            if target is not None and i < target:
                marker = " ".join(match[1].lower().split())
                boundaries.setdefault(target, marker)

    starts = [index for index, marker in boundaries.items() if marker == selector]
    if len(starts) != 1:
        raise ValueError(f"Could not locate a unique linked heading for {selector}")
    start = starts[0]
    following = [
        index for index, marker in boundaries.items()
        if index > start and (selector.startswith("item ") or not marker.startswith("item "))
    ]
    if following:
        end = min(following)
    elif selector == "part ii":
        end = len(nodes)
    else:
        raise ValueError(f"Could not locate the end of {selector}")

    paragraphs = []
    block = None
    for node in nodes[start:end]:
        if not isinstance(node, NavigableString) or isinstance(node, Comment):
            continue
        text = " ".join(node.split())
        if not text:
            continue
        parent = node.find_parent(_BLOCKS)
        if parent is not block or not paragraphs:
            paragraphs.append(text)
            block = parent
        else:
            paragraphs[-1] += " " + text
    paragraphs = [paragraph for paragraph in paragraphs if not _PAGE_FOOTER.fullmatch(paragraph)]
    if not paragraphs:
        raise ValueError(f"No text found under {selector}")
    return paragraphs


def filing_section(cik, accession, filename, form, section):
    section = " ".join(section.lower().split()).rstrip(".")
    if section not in SELECTORS.get(form, set()):
        raise ValueError("Use 10-K Item 1, 1A, 7, 7A or 8, or 10-Q Part I or II")
    paragraphs = _section_blocks(sec_client.tool_fetch_filing_text(cik, accession, filename), section)
    content = "\n".join(paragraphs)
    return {"cik": cik, "accession_number": accession, "filename": filename, "section": section,
            "text": content[:MAX_EXCERPT], "truncated": len(content) > MAX_EXCERPT}


def risk_factor_diff(cik):
    """Compare Item 1A in the latest two original annual filings."""
    filings = sec_client.filing_timeline(cik, form="10-K", limit=4)["filings"]
    by_period = {}
    for row in filings:
        if row["report_date"] and row["filename"]:
            by_period.setdefault(date.fromisoformat(row["report_date"]), row)
    periods = sorted(by_period, reverse=True)
    if len(periods) < 2 or not 300 <= (periods[0] - periods[1]).days <= 430:
        raise ValueError("Two consecutive annual report periods with primary documents are required")
    newer, older = (by_period[period] for period in periods[:2])
    old, new = (
        _section_blocks(sec_client.tool_fetch_filing_text(cik, row["accession_number"], row["filename"]), "item 1a")
        for row in (older, newer)
    )
    if max(len(old), len(new)) > 4_000:
        raise ValueError("Risk factor section exceeds the comparison size limit")
    change = "\n".join(unified_diff(old, new, fromfile=older["accession_number"],
                                    tofile=newer["accession_number"], n=0, lineterm=""))
    return {"older": older, "newer": newer, "section": "item 1a",
            "changed": bool(change), "diff": change[:MAX_EXCERPT], "truncated": len(change) > MAX_EXCERPT}
