"""Load selected SEC Company Facts and optionally the latest 10-K auditor into PostgreSQL."""

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

LOAD_SQL = Path(__file__).resolve().parents[1] / "db" / "load_sec.sql"
DEFAULT_CONCEPTS = ("us-gaap:Assets", "us-gaap:NetIncomeLoss", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")


def company_batch(ticker, concepts, include_auditors):
    cik = sec_client.resolve_cik(ticker)
    company = sec_client.company_facts(cik, parse_float=Decimal)
    batch = {"company": {"cik": cik, "ticker": ticker, "name": company["entityName"]},
             "filings": [], "facts": [], "auditors": []}
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

    if include_auditors:
        filing = sec_client.latest_10k(cik)
        accession = filing["accession_number"]
        html = sec_client.tool_fetch_filing_text(cik, accession, filing["filename"])
        soup = BeautifulSoup(html, "html.parser")
        names = {
            " ".join(tag.get_text(" ", strip=True).split())
            for tag in soup.find_all("ix:nonnumeric")
            if tag.get("name", "").lower() == "dei:auditorname" and not tag.has_attr("continuedat")
        }
        if names - {""}:
            batch["filings"].append({"accession": accession, "cik": cik,
                                     "form": "10-K", "filed_at": filing["filing_date"]})
            batch["auditors"] = [{"accession": accession, "key": name.casefold(), "label": name}
                                 for name in sorted(names - {""})]
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
    parser.add_argument("--latest-auditor", action="store_true", help="Read dei:AuditorName from the latest original 10-K")
    args = parser.parse_args()
    if any(not all(concept.split(":")) or concept.count(":") != 1 for concept in args.concept):
        parser.error("each concept must be TAXONOMY:CONCEPT")
    if not os.getenv("PGDATABASE"):
        parser.error("set PGDATABASE to choose the target database")
    batch = company_batch(args.ticker.strip().upper(), args.concept or DEFAULT_CONCEPTS, args.latest_auditor)
    load_batch(batch)
    print(f"Processed {len(batch['facts'])} fact observations and {len(batch['auditors'])} auditor assertions.")


if __name__ == "__main__":
    main()
