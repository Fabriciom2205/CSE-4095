"""Build frontend-ready statement visuals from reported figures."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import re
from typing import Literal

from pydantic import BaseModel

from propose import SYMBOL
import sec_client
import sec_statements

VisualKind = Literal["table", "bar", "line"]
StatementPeriod = Literal["annual", "quarter", "q4"]

_FORMAT = r"(?:bar|line)\s+(?:chart|graph|plot)|table|chart|graph|visual(?:ization)?"
_START = r"(?:^|[.!?;\n]\s*)(?:(?:can|could|would|will) you\s+)?(?:please\s+)?"
_VISUAL_REQUEST = re.compile(
    _START + r"(?:(?:make|create|draw|generate|render|show|give|provide|return|add|include)\s+"
    r"(?:(?:me|us)\s+)?(?:a\s+)?"
    + rf"(?P<format>{_FORMAT})\b|(?:show|present|summari[sz]e|compare|list|give|put|format|turn|convert)\s+"
    r"[^.!?;\n]{0,200}?\b(?:in|into|as)\s+(?:a\s+)?" + rf"(?P<inline>{_FORMAT})\b(?=\s*(?:$|[.!?;,\n]|with\b))"
    r"|(?P<plot>plot|chart|graph|visuali[sz]e)\s+\w|(?P<short>table|chart|graph)\s+please\b)",
    re.IGNORECASE,
)


def requested_visual(question: str) -> VisualKind | None:
    """Recognize direct visual requests in the current user question."""
    match = _VISUAL_REQUEST.search(question.strip())
    if not match:
        return None
    label = (match["format"] or match["inline"] or match["plot"] or match["short"]).lower()
    if label == "table":
        return "table"
    if label == "plot" or label.startswith("line"):
        return "line"
    return "bar"


class VisualSource(BaseModel):
    accession: str
    filed_at: date
    url: str
    role: Literal["reported", "full_year", "nine_months"]


class VisualCell(BaseModel):
    value: Decimal | None
    derived: bool = False
    period_start: date | None = None
    sources: list[VisualSource]


class VisualColumn(BaseModel):
    key: str
    label: str


class VisualRow(BaseModel):
    period_end: date
    period: StatementPeriod
    cells: dict[str, VisualCell]


class ResearchVisual(BaseModel):
    kind: VisualKind
    symbol: str
    statement: Literal["income_statement", "balance_sheet", "cash_flow"]
    title: str
    unit: str
    columns: list[VisualColumn]
    rows: list[VisualRow]


@dataclass
class VisualTurn:
    kind: VisualKind
    visuals: list[ResearchVisual] = field(default_factory=list)
    attempts: int = 0


def _fiscal_periods(cik, period, periods, period_ends, fiscal_years):
    if not 1 <= periods <= 8 or len(period_ends) > 8 or len(fiscal_years) > 8:
        raise ValueError("Provide one to eight fiscal periods")
    if period_ends and fiscal_years:
        raise ValueError("Select exact period ends or fiscal years")
    if fiscal_years and any(not 1900 <= year <= 9999 for year in fiscal_years):
        raise ValueError("Provide valid fiscal years")
    ends = sorted({date.fromisoformat(day).isoformat() for day in period_ends})
    if ends and period != "quarter":
        return [(end, period) for end in ends]
    # Exact quarter-end requests also need the fiscal-year timeline to identify Q4.
    limit = 50 if period_ends or fiscal_years else periods + 1
    annual = sec_client.filing_timeline(cik, form="10-K", limit=limit)["filings"]
    by_date = {row["report_date"]: ("q4" if period in ("quarter", "q4") else "annual")
               for row in annual if row["report_date"]}
    if period == "quarter":
        if ends:
            return [(end, by_date.get(end, "quarter")) for end in ends]
        quarters = sec_client.filing_timeline(cik, form="10-Q", limit=limit)["filings"]
        for row in quarters:
            if row["report_date"]:
                by_date.setdefault(row["report_date"], "quarter")
    if fiscal_years:
        by_date = {end: kind for end, kind in by_date.items() if date.fromisoformat(end).year in fiscal_years}
        if period == "quarter" and len(by_date) > 8:
            raise ValueError("Select at most eight quarters")
        return sorted(by_date.items())
    return sorted(sorted(by_date.items(), reverse=True)[:periods])


def statement_visual(kind, symbol, statement, line_items, period, periods, period_ends, fiscal_years, currency):
    symbol = symbol.strip().upper()
    if not re.fullmatch(SYMBOL, symbol):
        raise ValueError("Provide a stock ticker")
    if statement not in sec_statements.STATEMENTS:
        raise ValueError("Choose income_statement, balance_sheet, or cash_flow")
    if len(line_items) > len(sec_statements.STATEMENTS[statement]):
        raise ValueError("Select up to three supported statement lines")
    cik = sec_client.resolve_cik(symbol)
    selected = _fiscal_periods(cik, period, periods, period_ends, fiscal_years)
    if not selected:
        raise ValueError("No matching SEC report periods were found")
    series = sec_statements.company_statements(cik, statement, selected, currency, line_items=line_items)
    if all(line["value"] is None for point in series for line in point["lines"].values()):
        raise ValueError("No supported statement values were found for the requested periods")
    rows = []
    for point in series:
        cells = {}
        for name, item in point["lines"].items():
            sources = []
            for source in item.get("sources", []):
                accession = sec_client._validate_accession(source["accession"])
                url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{accession}-index.html"
                sources.append(VisualSource(**source, url=url))
            cells[name] = VisualCell(value=item["value"], derived=item.get("derived", False),
                                     period_start=item.get("period_start"), sources=sources)
        rows.append(VisualRow(period_end=point["period_end"], period=point["period"], cells=cells))
    return ResearchVisual(kind=kind, symbol=symbol, statement=statement, unit=currency,
                          title=f"{symbol} {statement.replace('_', ' ')}",
                          columns=[VisualColumn(key=name, label=name.replace("_", " ").capitalize())
                                   for name in rows[0].cells], rows=rows)
