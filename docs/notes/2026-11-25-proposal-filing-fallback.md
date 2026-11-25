# Worklog: Direct filing fallback for proposals

* **Date:** 2026-11-25
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Recover proposal evidence when semantic filing search fails.

## Changes Implemented

* [Proposal runtime](../../python-brain/adk_runtime.py) falls back to a bounded Item 1A excerpt from the latest original SEC 10-K and logs the symbol and underlying exception type.

## Key Decisions & Context

The local logs showed repeated SEC tool errors. A replay with the same form values succeeded, so the exact original exception remains unknown. With a simulated search failure, direct EDGAR retrieval returned excerpts for both AAPL and NVDA. The API service was restarted.

## Known Gotchas, Blockers & Environment Issues

The fallback still needs EDGAR access and recognizable Item 1A text. It does not replace independently required quote evidence or risk checks.

## Next Steps (Handoff Checklist)

* [ ] If failures recur, inspect the fallback log for the ticker and search exception type.
