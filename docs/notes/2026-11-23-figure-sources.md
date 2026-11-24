# Worklog: SEC Figure Source research

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Implemented

## Objective

Let the research agent answer ownership and holdings questions about public figures or institutional managers using primary SEC filings.

## Changes Implemented

* Added [figure_sources.py](../../python-brain/figure_sources.py) for Form 4 transaction extraction and consecutive 13F holdings comparisons. Retained transaction and filing dates, reporting owner attribution, and source accessions.
* Registered a read-only MCP lookup and exposed it to the existing Gemini agent and ADK SEC specialist. Figure questions can use the research HTTP route without a ticker.
* Added [regressions](../../python-brain/tests/test_figure_sources.py) for Form 4 gift classification and ownership, verified source citations, and 13F restatement and amendment behavior. Live EDGAR lookups returned records for Berkshire Hathaway, Pershing Square, and Jeff Bezos. An authenticated ADK request without a ticker returned a Berkshire comparison with both SEC accessions.

## Key Decisions & Context

Resolve a small set of aliases or accept an exact SEC filer CIK. Keep reported transactions distinct from quarter-to-quarter changes. Rank 13F changes by the larger of the two reported holding values and preserve the compared quantities.

All 98 Python discovery tests passed with disposable PostgreSQL, as did both SQL checks and the existing SEC and MCP scripts.

## Known Gotchas, Blockers & Environment Issues

Holdings differences can reflect splits, security identity changes, or disclosure changes. Form 4 reports and amendments are displayed as filed. Congressional disclosures remain outside this SEC integration.

## Next Steps (Handoff Checklist)

* [ ] Add aliases only as needed. Assess applicable use terms separately before adding congressional disclosures.
