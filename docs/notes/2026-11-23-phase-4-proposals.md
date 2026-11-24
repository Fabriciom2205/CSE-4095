# Worklog: Phase 4 portfolio proposals

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Implemented

## Objective

Verify a populated paper position and enable target-weight proposals without model-based order sizing or approval.

## Changes Implemented

* Matched quantity, market value, cost basis, and unrealized P&L from a live Alpaca paper position against the provider payload after a fill.
* Added [portfolio_view.py](../../python-brain/portfolio_view.py) to expose USD equity, a caller-supplied historical peak, and signed position market values.
* Added the proposal schema, pure whole-share order constructor, and deterministic exposure validation in [propose.py](../../python-brain/propose.py).
* Added a private [proposal session](../../python-brain/agent.py) with the snapshot and validation tools and locally validated structured output.
* Accepted an optional Alpaca /v2 endpoint suffix while preserving exact host allowlisting.
* Passed all 67 Python discovery tests with pgvector enabled and both SQL checks on disposable PostgreSQL.

## Key Decisions & Context

The proposal tools evaluate dollar targets and preserve unlisted holdings. Hypothetical share sizing remains an independent pure function. The private tools are absent from the default research agent and MCP server. The dedicated session sends minimal portfolio state to the configured model. The live model smoke test used synthetic portfolio data.

## Known Gotchas, Blockers & Environment Issues

Peak equity comes from the trusted caller. Sector limits cannot run until sector classifications are available. Proposal validation is informational and does not place or approve orders.

## Next Steps (Handoff Checklist)

* [ ] Provide a trusted equity history source and sector classifications before enabling those automatic inputs.
