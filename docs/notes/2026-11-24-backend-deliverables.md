# Worklog: Backend deliverables and live verification

* **Date:** 2026-11-24
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed for the repository changes below

## Objective

Reconcile the open research and portfolio notes with the current backend and implement the deliverables that fit the existing data and runtime layers.

## Changes Implemented

* [SEC importer](../../python-brain/ingest_sec.py) reads historical tagged auditors and selected monetary facts in standard explicit segment and geographic contexts. It writes the complete qualified axis and member combination, units, periods, value, and filing provenance into existing relationship tables. `sec_relations` reaches the stored rows from the research specialist.
* [Filing search](../../python-brain/filing_rag.py) retrieves excerpts from 2–8 recent original report periods. It issues one query embedding and one pgvector search, groups repeated excerpts by normalized case and whitespace, and returns filing coverage alongside evidence. Missing indexes remain visible and can be seeded through the existing writer workflow.
* [Proposal API](../../python-brain/api.py) can read account-scoped historical peak equity with a dedicated read-only DSN. The read uses the same account identity and observation time as the portfolio snapshot. The separately authorized recorder supplies the history.
* [Filing navigation](../../python-brain/filing_sections.py) accepts descriptive anchor IDs when visible text omits an item or part number. The archive URL and cache eviction smoke checks now run production code.
* [Live checks](../../python-brain/tests/live/) include repeatable filing-plus-quote benchmarks and two synthetic prompt-injection fixtures evaluated against Gemini.

## Key Decisions & Context

The initial dimensional scope is standard US GAAP monetary facts from extracted XBRL instances, with explicit members on recognized segment and geography axes. It preserves every explicit axis and member on included contexts. Cross-filing retrieval reads published indexes only. Neither change needs a schema migration.

A live Microsoft import into disposable PostgreSQL loaded 144 consolidated facts, three auditor assertions, and 24 dimensional assertions. Linked section validation covered annual Item 1A and quarterly Part II for Apple, Microsoft, and NVIDIA. Live MCP ran in-process, over stdio, and over streamable HTTP. Both adversarial filing cases passed. The Microsoft mixed SEC/Finnhub benchmark produced both citations in cold and warm runs. The cold run used 45 embedding requests and took 14.79 seconds. The warm run used one embedding request and took 6.42 seconds. Both runs used two generation calls.

Statement checks matched PostgreSQL and EDGAR results for saved Apple, Microsoft, and SAP filing data. SAP's Q4 income and cash flow remained unavailable because the sources lacked the required comparable periods.

All 111 Python discovery tests and both PostgreSQL SQL checks passed.

## Known Gotchas, Blockers & Environment Issues

History coverage depends on stored indexes and exact-passage matching. Numeric coverage depends on issuer tagging and excludes custom fact concepts and typed members. The HTTP equity reader needs deployment configuration and seeded history. The benchmark records observed token usage and elapsed time. Billed dollars are still unmeasured.

## Next Steps (Handoff Checklist)

* [ ] Expand real issuer, statement, and filing-period coverage. Measure deployment bills and add more research and adversarial cases.
* [ ] Configure the deployment credentials and shared execution ledger. Run the approved paper replay during regular market hours.
* [x] Define snapshot retention, use EDGAR sector classifications, and add shared MCP access controls. [Implementation](2026-11-24-voice-and-portfolio-controls.md)
