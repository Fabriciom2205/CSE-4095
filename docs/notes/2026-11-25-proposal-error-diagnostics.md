# Worklog: Proposal error diagnostics

* **Date:** 2026-11-25
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Investigate the generic proposal error and make a recurrence easier to diagnose.

## Changes Implemented

* [Proposal runtime](../../python-brain/adk_runtime.py) reports SEC and Finnhub collection failures separately and explicitly rejects a run without a final model answer.
* [HTTP API](../../python-brain/api.py) returns a message for the failing stage and logs exception types without logging provider payloads.

## Key Decisions & Context

The original request returned HTTP 502 without a completed evidence collection log. The exact exception was suppressed. Independent SEC and Finnhub lookups and a disposable model session succeeded. After the local service restart, an authenticated proposal for AAPL and NVDA with a sector cap returned HTTP 200 and two hypothetical targets. The HTTP check left the drawdown field blank.

## Known Gotchas, Blockers & Environment Issues

The original provider failure did not recur. Existing evidence and risk validation remain required.

## Next Steps (Handoff Checklist)

* [ ] If the error recurs, use the source and exception type in the API log to narrow down the failure.
