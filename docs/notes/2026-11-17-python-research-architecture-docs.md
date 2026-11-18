# Worklog: Python research architecture documentation

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Complete

## Objective

Update the main project documentation and architecture diagram to reflect the Python research workflow.

## Changes Implemented

* [README](../../README.md) describes live EDGAR research, verified Cloud SQL filing retrieval, and the PostgreSQL health check.
* [Architecture](../ARCHITECTURE.md) shows the Python agent and MCP server sharing research tools. The diagram shows EDGAR lookups, Gemini embeddings, Cloud SQL reuse, and the planned frontend API.

## Key Decisions & Context

Rust, backtesting, and execution remain deferred in the current architecture. Earlier design decisions remain in the ADR history.

## Known Gotchas, Blockers & Environment Issues

The React Research page still uses mock data. Cloud SQL filing retrieval has been verified from the Python backend.

## Next Steps (Handoff Checklist)

* [ ] Add the Python HTTP API and connect the frontend Research page.
