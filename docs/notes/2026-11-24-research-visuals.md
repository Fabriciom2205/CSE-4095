# Worklog: Opt-in SEC research visuals

* **Date:** 2026-11-24
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Let clients request a renderable SEC financial table or chart through the existing research API.

## Changes Implemented

* [HTTP research contract](../../python-brain/api.py) accepts an explicit visual format or a direct visual request in the question. Successful visuals appear in the normal JSON response or the streaming final event.
* [ADK runtime](../../python-brain/adk_runtime.py) enables the statement visual tool for the requesting turn. It carries returned filing sources into research citations. A later prose turn has no visual tool or visual fields.
* [Statement visual builder](../../python-brain/research_visuals.py) returns column labels, exact decimal strings, fiscal dates, currency, missing cells, and cell-level accession links. The [typed statement reader](../../python-brain/sec_statements.py) resolves several requested periods in one SQL read and one EDGAR fallback.
* [Local Setup](../LOCAL_SETUP.md#research-tables-and-charts) documents the request and frontend response.

## Key Decisions & Context

The backend returns chart data and a format. The browser supplies rendering. Annual and quarterly data retain their fiscal period types. A derived Q4 cell retains both input filings. Existing statement coverage determines what can be rendered.

An authenticated live Apple request returned a three-year revenue and operating income table. “Plot it” in the same session streamed an identical series as a line chart. A subsequent prose question omitted the visual field. The application used an isolated SQLite session and live SEC Company Facts.

All 115 Python tests and both PostgreSQL checks passed.

## Known Gotchas, Blockers & Environment Issues

Visuals cover supported income statement, balance sheet, and cash flow lines up to eight periods. Reproducing a filing's arbitrary HTML or footnote table requires a separate extractor.

## Next Steps (Handoff Checklist)

* [ ] Render the typed table and chart payloads when implementing the final frontend.
