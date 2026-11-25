# Worklog: Investing dashboard and paper orders

* **Date:** 2026-11-24
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Make investing the frontend home, add dedicated SEC filings and strategy pages, and keep Phil available as a dismissible voice-enabled floating chat.

## Changes Implemented

* Rebuilt `frontend/src/App.tsx` around account performance, seven Alpaca history periods, buying power, current holdings, stock and ETF discovery, and dedicated asset views.
* Added a two-step, confirmed paper limit-order flow that posts to the authenticated API and preserves the idempotency key for an uncertain order response.
* Added filing search filters and a UI for the existing deterministic moving-average replay endpoint.
* Changed Phil to a floating launcher with a first-visit teaser, close/minimize behavior, typed research, citations, and microphone transcription.
* Added authenticated Alpaca history, asset details, paper order, and strategy replay endpoints. The paper order route reuses the existing database ledger, caps, risk checks, halt switch, and paper endpoint enforcement.
* Updated API route expectations, frontend and architecture docs, and amended [ADR 0004](../decisions/0004-portfolio-and-deterministic-strategy.md) for the authenticated paper-only API boundary.

## Key Decisions & Context

Portfolio performance comes from Alpaca's account-history endpoint, not a derived estimate from current holdings. Paper orders require operator confirmation and are limited by the backend to whole-share US equities/ETFs through Alpaca's paper endpoint. A shared bearer token is still the API's identity boundary; the hosted private API must not be exposed to a browser until an appropriate browser access and per-user identity path is configured.

## Known Gotchas, Blockers & Environment Issues

* `npm run build` and `npm run astryx -- doctor --built src` pass. Astryx doctor reports a purity warning for custom chart SVG and semantic HTML styling; no failures.
* The Vite production bundle is about 674 kB and emits the existing large-chunk warning.
* Python modules passed `py_compile`; unit tests and a real order were not run. The browser order path must only be exercised against an Alpaca paper account.

## Next Steps (Handoff Checklist)

* [ ] Configure a secure browser access path and per-user identity before using paper orders through hosted Cloud Run.
* [ ] Manually review market data, account history periods, responsive layout, voice input, and paper order confirmation in the browser.
