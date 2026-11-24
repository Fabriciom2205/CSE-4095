# Worklog: Typed SEC research and filing discovery

* **Date:** 2026-11-20
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Implemented and checked against a disposable database

## Objective

Let the agent sequence financial facts, reported relationships, filing discovery, narrative retrieval, and market data.

## Changes Implemented

* Added the typed fact and relationship reads in [filing_store.py](../../python-brain/filing_store.py) and the statement concept map and EDGAR fallback in [sec_statements.py](../../python-brain/sec_statements.py).
* Registered statement and relationship tools in [mcp_server.py](../../python-brain/mcp_server.py). The [agent](../../python-brain/agent.py) can pass EFTS search hits into filing RAG.
* Added the reader alias, in-memory RAG fallback, and the importer option to seed mapped tags and shares outstanding. See [PostgreSQL setup](../POSTGRESQL.md#read-consolidated-facts-and-relationships).

## Key Decisions & Context

* EDGAR remains the default for facts. The new reader variable opts into the SQL path. The tools select data sources and handle fallback.
* Statement reads apply the expected unit and period kind, use the latest filing per context, and mark conflicting observations as unresolved. Q4 flow lines cite the full-year and nine-month observations. Relationship reads use the reported view and return historical evidence.
* Seeded 4,269 observations from real SEC Company Facts for Apple, Microsoft, and SAP into a disposable PostgreSQL cluster. Statement output matched between the EDGAR and SQL paths for inspected annual and quarterly periods, including Apple and Microsoft Q4 and SAP annual EUR. This check compared transport and normalization on the same underlying data.

## Known Gotchas, Blockers & Environment Issues

* Apple's standalone fiscal Q3 cash flow and SAP's Q4 flows lacked qualifying observations in the checked Company Facts data. The tools returned explicit missing lines.
* The local PostgreSQL instance did not have pgvector. The offline suite checked the reader alias and in-memory fallback. A read-only PostgreSQL role exercised the new MCP fact, statement, and relationship calls.
* Relationship coverage depends on existing imports. Production and Cloud SQL data were not changed.

## Next Steps (Handoff Checklist)

* [ ] Expand filing coverage across issuers and refresh the opted-in database before relying on it for recent filings.
* [ ] Add dimensional and historical relationship imports to grow `sec_relations` coverage.
