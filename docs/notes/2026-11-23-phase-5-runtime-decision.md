# Worklog: Phase 5 agent and API decision

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Proposed for review

## Objective

Decide whether Phase 5 needs a migration to ADK before serving the frontend contract.

## Changes Implemented

Drafted [ADR 0005](../decisions/0005-phase-5-api-and-agent-runtime.md). It proposes typed FastAPI routes over the existing Gemini agent, with bearer auth, bounded portfolio caching, explicit freshness status, and a separate local paper execution boundary.

## Key Decisions & Context

The SDK has per-chat history and supports streaming. ADK would add session services and an event runtime. The proposed initial contract is single-turn JSON with an agent runtime that can be swapped later.

## Known Gotchas, Blockers & Environment Issues

No API code was written during the architecture review. Provider fetch time does not establish the time of a portfolio mark. Drawdown still needs a trusted equity peak.

## Next Steps (Handoff Checklist)

* [ ] Confirm whether durable conversations or tool-event streaming are required in the first API release.
* [ ] Implement and verify the six OpenAPI routes after choosing the runtime.
