# Worklog: Full backend feature UI and formatted Phil

* **Date:** 2026-11-24
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Audit the Python HTTP API and related research, portfolio, and strategy capabilities, then expose the useful workflows in the React frontend without creating a live trading path.

## Changes Implemented

* Added a per-request-confirmed `/agent/paper-run` route that exposes the existing agent execution mode while forcing paper execution and preserving the supplied decision key.
* Added authenticated broker-order history and API health status to the investing page.
* Added proposal-only portfolio analysis and risk constraint inputs, separate from agent paper execution.
* Added configurable, named moving-average strategy drafts saved in browser storage, a Phil-assisted strategy design prompt, adjustable replay parameters, and saved-snapshot replay.
* Changed Phil research to consume server-sent events, format Markdown safely, show citations, and render structured SEC table, bar, and line visuals with filing source links. Added an automatic/explicit visual selector in the chat composer.
* Updated API route expectations, ADR 0004, frontend guidance, project overview, and backlog handoff.

## Key Decisions & Context

Proposal-only analysis never submits an order. Agent paper execution is a separate authenticated operation that requires `confirm_paper_only: true`, a selected symbol, user prompt, and decision key, then calls the existing paper execution runner with its database ledger, risk controls, halt switch, and forced Alpaca paper endpoint. Strategy drafts remain browser-local because the backend has no strategy persistence API and currently supports one deterministic moving-average engine with adjustable inputs.

## Known Gotchas, Blockers & Environment Issues

* Frontend build and Astryx doctor pass with warnings for native semantic tables/chart SVG and source styling; there are no doctor failures.
* The frontend bundle remains above Vite's 500 kB advisory threshold.
* Python syntax compilation passed. Unit tests, browser review, and paper-order submissions were not run. Cloud Run was not updated.
* Hosted browser access still requires a secure per-user identity boundary; the current API uses a shared bearer token.

## Next Steps (Handoff Checklist)

* [ ] Configure secure browser access and per-user identity before exposing paper execution through hosted Cloud Run.
* [ ] Manually review visual rendering, streamed Phil responses, proposal validation, strategy drafts, and paper-only flow in the browser.
