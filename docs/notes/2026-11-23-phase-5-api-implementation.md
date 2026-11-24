# Worklog: Phase 5 FastAPI and ADK implementation

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Implemented and verified locally

## Objective

Publish the typed HTTP contract and add specialist agents and durable conversations without exposing execution.

## Changes Implemented

* [adk_runtime.py](../../python-brain/adk_runtime.py) adds a coordinator, SEC and market specialists, and a separate schema-constrained proposal agent. Sessions use ADK database storage and context compaction.
* [api.py](../../python-brain/api.py) serves the six typed routes, bearer authentication, research JSON and SSE, a 15-second Alpaca cache, and explicit quote freshness.
* [test_api.py](../../python-brain/tests/test_api.py) covers OpenAPI, auth, sessions, SSE, proposal breaches, cached portfolio reads, and replay from server-owned files.
* Updated the [setup guide](../LOCAL_SETUP.md#phase-5-http-api), requirements, and [ADR 0005](../decisions/0005-phase-5-api-and-agent-runtime.md).

## Key Decisions & Context

The installed ADK release requires Google Gen AI SDK 2.x. Existing CLI and MCP entry points remain available and were included in compatibility checks. Browser API sessions have no execution access. Read-only brokerage state is evaluated outside the ADK proposal prompt.

## Known Gotchas, Blockers & Environment Issues

All 81 Python tests and both SQL checks passed on disposable PostgreSQL with pgvector. A live NVDA proposal returned validated evidence and freshness metadata. A follow-up recovered an earlier turn after restarting Uvicorn against PostgreSQL and returned the final SSE event. No Cloud SQL schema changes were made.

## Next Steps (Handoff Checklist)

* [ ] Set the operator bearer token and configure a dedicated session database for the intended deployment.
* [ ] Add Phase 6 snapshot persistence and audit retention once the HTTP contract is adopted.
