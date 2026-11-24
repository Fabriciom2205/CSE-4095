"""Typed SEC financial reads shared by the MCP server and research agent."""

import logging
import os
import re
from datetime import date, timedelta
from decimal import Decimal

import filing_store
import sec_client

TAXONOMIES = ("us-gaap", "dei", "ifrs-full")
# Ordered equivalent tags per line. Flow lines are additive across periods.
STATEMENTS = {
    "balance_sheet": {
        "assets": ("us-gaap:Assets", "ifrs-full:Assets"),
        "liabilities": ("us-gaap:Liabilities", "ifrs-full:Liabilities"),
        "equity": ("us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
                   "us-gaap:StockholdersEquity", "ifrs-full:Equity"),
    },
    "income_statement": {
        "revenue": ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "us-gaap:Revenues",
                    "us-gaap:SalesRevenueNet", "ifrs-full:Revenue"),
        "operating_income": ("us-gaap:OperatingIncomeLoss", "ifrs-full:ProfitLossFromOperatingActivities"),
        "net_income": ("us-gaap:ProfitLoss", "us-gaap:NetIncomeLoss", "ifrs-full:ProfitLoss"),
    },
    "cash_flow": {
        "operating_cash_flow": ("us-gaap:NetCashProvidedByUsedInOperatingActivities",
                                "ifrs-full:CashFlowsFromUsedInOperatingActivities"),
        "investing_cash_flow": ("us-gaap:NetCashProvidedByUsedInInvestingActivities",
                                "ifrs-full:CashFlowsFromUsedInInvestingActivities"),
        "financing_cash_flow": ("us-gaap:NetCashProvidedByUsedInFinancingActivities",
                                "ifrs-full:CashFlowsFromUsedInFinancingActivities"),
    },
}
log = logging.getLogger(__name__)


def _read_facts(cik, selectors, **filters):
    # A separate opt-in keeps existing filing-index readers on the EDGAR facts default.
    dsn = os.getenv("SEC_DB_READ_DSN")
    if dsn:
        try:
            return filing_store.query_facts(dsn, cik, selectors, **filters)
        except filing_store.FilingStoreError as error:
            log.warning("%s; using SEC Company Facts", error)
    return []


def get_financial_facts(cik, concept):
    cik = sec_client._validate_cik(cik)
    if not isinstance(concept, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,199}", concept):
        raise ValueError("Invalid financial concept")
    rows = _read_facts(cik, [(taxonomy, concept, None) for taxonomy in TAXONOMIES])
    for taxonomy in TAXONOMIES:
        units = {}
        for row_taxonomy, _, unit, start, end, value, accession, filed, form, _ in rows:
            if row_taxonomy != taxonomy:
                continue
            points = units.setdefault(unit, [])
            if len(points) < 5:
                point = {"end": end.isoformat(), "val": int(value) if value == int(value) else float(value),
                         "accn": accession, "filed": filed.isoformat(), "form": form}
                if start:
                    point["start"] = start.isoformat()
                points.append(point)
        if units:
            for points in units.values():
                points.reverse()
            return {"label": concept, "description": "", "units": units}
    return sec_client.tool_get_financial_facts(cik, concept)


def _edgar_rows(cik, selectors, first_end, last_end, instant):
    facts = sec_client.company_facts(cik, parse_float=Decimal).get("facts", {})
    for taxonomy, concept, unit in selectors:
        item = facts.get(taxonomy, {}).get(concept, {})
        for point in item.get("units", {}).get(unit, []):
            start = date.fromisoformat(point["start"]) if point.get("start") else None
            end = date.fromisoformat(point["end"])
            value = point.get("val")
            if (start is None) == instant and first_end <= end <= last_end and type(value) in (int, Decimal):
                yield (taxonomy, concept, unit, start, end, Decimal(value), point["accn"],
                       date.fromisoformat(point["filed"]), point["form"], point["form"] in ("10-Q", "10-Q/A"))


def _latest(rows):
    if rows:
        filed = max(row[7] for row in rows)
        latest = [row for row in rows if row[7] == filed]
        if len({(row[3], row[4], row[5]) for row in latest}) == 1:
            return max(latest, key=lambda row: row[6])
    return None


def _duration(row):
    return (row[4] - row[3]).days + 1


def _statement_lines(rows, mapping, end, period, instant, unit):
    lines = {}
    for name, tags in mapping.items():
        for tag in tags:
            candidates = [row for row in rows if ":".join(row[:2]) == tag]
            if instant:
                current = [row for row in candidates if row[4] == end]
            elif period in ("annual", "q4"):
                current = [row for row in candidates if row[4] == end and 350 <= _duration(row) <= 380]
            else:
                current = [row for row in candidates if row[4] == end and 75 <= _duration(row) <= 105]
                # A Q4 tagged in an annual report must never serve as a direct quarterly fact.
                if not any(row[9] for row in current):
                    current = []
            if not current:
                continue
            observation = _latest(current)
            if observation is None:
                break
            _, _, _, start, _, value, accession, filed, _, _ = observation
            sources = [{"accession": accession, "filed_at": filed.isoformat(), "role": "reported"}]
            derived = period == "q4" and not instant
            if derived:
                nine_months = _latest([
                    row for row in candidates if row[3] == start
                    and 260 <= _duration(row) <= 290 and 75 <= (end - row[4]).days <= 105
                ])
                if nine_months is None:
                    continue
                value -= nine_months[5]
                start = nine_months[4] + timedelta(days=1)
                sources[0]["role"] = "full_year"
                sources.append({"accession": nine_months[6], "filed_at": nine_months[7].isoformat(),
                                "role": "nine_months"})
            lines[name] = {"tag": tag, "unit": unit, "value": str(value), "derived": derived,
                           "period_start": start.isoformat() if start else None, "sources": sources}
            break
        if name not in lines:
            lines[name] = {"unit": unit, "value": None, "status": "missing_or_ambiguous"}
    return lines


def company_statement(cik, statement, period_end, period, currency):
    return company_statements(cik, statement, [(period_end, period)], currency)[0]


def company_statements(cik, statement, periods, currency, *, line_items=()):
    """Read several fiscal periods with one SQL lookup and one read-through fallback."""
    cik = sec_client._validate_cik(cik)
    if statement not in STATEMENTS:
        raise ValueError("Statement must be balance_sheet, income_statement, or cash_flow")
    if not 1 <= len(periods) <= 8:
        raise ValueError("Provide one to eight fiscal periods")
    if any(period not in ("annual", "quarter", "q4") for _, period in periods):
        raise ValueError("Period must be annual, quarter (Q1–Q3), or q4")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Currency must be a three-letter uppercase code")
    instant = statement == "balance_sheet"
    mapping = STATEMENTS[statement]
    if line_items:
        if any(name not in mapping for name in line_items):
            raise ValueError(f"Available lines: {', '.join(mapping)}")
        mapping = {name: mapping[name] for name in line_items}
    periods = [(date.fromisoformat(end), period) for end, period in periods]
    first_end = min(end - timedelta(days=105) if period == "q4" and not instant else end for end, period in periods)
    last_end = max(end for end, _ in periods)
    selectors = list(dict.fromkeys((*tag.split(":"), currency) for tags in mapping.values() for tag in tags))
    rows = _read_facts(cik, selectors, first_end=first_end, last_end=last_end, instant=instant)
    series = [_statement_lines(rows, mapping, end, period, instant, currency) for end, period in periods]
    if any(line["value"] is None for lines in series for line in lines.values()):
        edgar = list(_edgar_rows(cik, selectors, first_end, last_end, instant))
        for (end, period), lines in zip(periods, series, strict=True):
            if any(line["value"] is None for line in lines.values()):
                fallback = _statement_lines(edgar, mapping, end, period, instant, currency)
                lines.update((name, line) for name, line in fallback.items() if line["value"] is not None)
    return [{"cik": cik, "statement": statement, "period": period, "period_end": end.isoformat(), "lines": lines}
            for (end, period), lines in zip(periods, series, strict=True)]
