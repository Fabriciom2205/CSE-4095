# Worklog: Live provider verification

* **Date:** 2026-11-22
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Live read and replay checks passed

## Objective

Verify Alpaca, Massive, and Finnhub after credentials were configured.

## Changes Implemented

* Verified Alpaca paper account, positions, and orders using read-only requests. Both collections were empty.
* Captured raw Massive SPY daily bars for 2025-01-01 through 2025-12-31. Two CLI replays of the saved snapshot were byte identical across 250 sessions and 27 simulated fills.
* Verified a live Finnhub AAPL quote.

## Key Decisions & Context

The existing Alpaca setting includes a /v2 suffix. Used a process-only override pointing to the paper API root. The client appends the endpoint paths.

## Known Gotchas, Blockers & Environment Issues

The live paper account has no positions or orders to validate field mapping against. Mock tests cover populated records.

## Next Steps (Handoff Checklist)

* [ ] Set ALPACA_BASE_URL to https://paper-api.alpaca.markets in the local environment and verify populated paper account reads when available.
