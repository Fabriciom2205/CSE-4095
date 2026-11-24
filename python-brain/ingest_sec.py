"""Load selected SEC Company Facts and optional 10-K auditor history into PostgreSQL."""

import argparse
import csv
from decimal import Decimal
import io
import json
import os
from pathlib import Path
import subprocess

from bs4 import BeautifulSoup

import sec_client
from sec_dimensions import dimensions_from_instance
from sec_statements import STATEMENTS

LOAD_SQL = Path(__file__).resolve().parents[1] / "db" / "load_sec.sql"
DEFAULT_CONCEPTS = ("us-gaap:Assets", "us-gaap:NetIncomeLoss", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")


def company_batch(ticker, concepts, include_auditors, *, auditor_filings=0, dimensions_form=None):
    cik = sec_client.resolve_cik(ticker)
    company = sec_client.company_facts(cik, parse_float=Decimal)
    batch = {"company": {"cik": cik, "ticker": ticker, "name": company["entityName"]},
             "filings": [], "facts": [], "auditors": [], "dimensions": []}
    if company.get("cik") != int(cik):
        raise ValueError("SEC Company Facts returned a different CIK")
    for selector in dict.fromkeys(concepts):
        taxonomy, _, concept = selector.partition(":")
        metric = company["facts"].get(taxonomy, {}).get(concept, {})
        for unit, points in metric.get("units", {}).items():
            for point in points:
                value = point.get("val")
                if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
                    continue
                accession = point["accn"]
                batch["filings"].append({"accession": accession, "cik": cik,
                                         "form": point["form"], "filed_at": point["filed"]})
                batch["facts"].append({"accession": accession, "taxonomy": taxonomy, "concept": concept,
                                       "unit": unit, "period_start": point.get("start"),
                                       "period_end": point["end"], "value": str(value)})

    if auditor_filings:
        filings = sec_client.filing_timeline(cik, form="10-K", limit=auditor_filings)["filings"]
    else:
        filings = [sec_client.latest_10k(cik)] if include_auditors else []
    for filing in filings:
        if not filing["filename"]:
            continue
        accession = filing["accession_number"]
        html = sec_client.tool_fetch_filing_text(cik, accession, filing["filename"])
        soup = BeautifulSoup(html, "html.parser")
        names = {
            " ".join(tag.get_text().split())
            for tag in soup.find_all("ix:nonnumeric")
            if tag.get("name", "").lower() == "dei:auditorname" and not tag.has_attr("continuedat")
        }
        if names - {""}:
            batch["filings"].append({"accession": accession, "cik": cik,
                                     "form": "10-K", "filed_at": filing["filing_date"]})
            batch["auditors"].extend({"accession": accession, "key": name.casefold(), "label": name}
                                     for name in sorted(names - {""}))
    if dimensions_form:
        filing = sec_client.latest_filing(cik, dimensions_form)
        accession = filing["accession_number"]
        primary, suffix = filing["filename"].rsplit(".", 1)
        if suffix.lower() not in {"htm", "html"}:
            raise ValueError("Expected an SEC inline XBRL primary document")
        instance = f"{primary}_{suffix.lower()}.xml"
        xml = sec_client.tool_fetch_filing_text(cik, accession, instance)
        dimensions = dimensions_from_instance(xml, cik, accession)
        if dimensions:
            batch["filings"].append({"accession": accession, "cik": cik,
                                     "form": dimensions_form, "filed_at": filing["filing_date"]})
            batch["dimensions"] = dimensions
    return batch


def load_batch(batch):
    csv_input = io.StringIO()
    csv.writer(csv_input).writerow([json.dumps(batch)])
    subprocess.run(
        ["psql", "-X", "--no-password", "--single-transaction", "-v", "ON_ERROR_STOP=1",
         "-c", "CREATE TEMP TABLE sec_batch (payload jsonb)",
         "-c", "COPY sec_batch FROM STDIN WITH (FORMAT csv)", "-f", str(LOAD_SQL)],
        input=csv_input.getvalue(), text=True, check=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker")
    parser.add_argument("concept", metavar="TAXONOMY:CONCEPT", nargs="*")
    parser.add_argument("--statement-facts", action="store_true", help="Include the mapped statement concepts and shares outstanding")
    auditors = parser.add_mutually_exclusive_group()
    auditors.add_argument("--latest-auditor", action="store_true", help="Read dei:AuditorName from the latest original 10-K")
    auditors.add_argument("--auditor-filings", type=int, choices=range(1, 21), metavar="N",
                          help="Read dei:AuditorName from up to N original 10-Ks (1–20)")
    parser.add_argument("--dimensions-form", choices=("10-K", "10-Q"),
                        help="Load standard dimensional facts from the latest original filing of this form")
    args = parser.parse_args()
    if any(not all(concept.split(":")) or concept.count(":") != 1 for concept in args.concept):
        parser.error("each concept must be TAXONOMY:CONCEPT")
    if not os.getenv("PGDATABASE"):
        parser.error("set PGDATABASE to choose the target database")
    concepts = list(args.concept or DEFAULT_CONCEPTS)
    if args.statement_facts:
        concepts.extend(tag for statement in STATEMENTS.values() for tags in statement.values() for tag in tags)
        concepts.append("dei:EntityCommonStockSharesOutstanding")
    batch = company_batch(args.ticker.strip().upper(), concepts, args.latest_auditor,
                          auditor_filings=args.auditor_filings or 0, dimensions_form=args.dimensions_form)
    load_batch(batch)
    print(f"Processed {len(batch['facts'])} fact observations, {len(batch['auditors'])} auditor assertions "
          f"and {len(batch['dimensions'])} dimensional assertions.")


if __name__ == "__main__":
    main()
