# Worklog: README architecture diagram

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Complete

## Objective

Show the active Python research architecture on the repository landing page.

## Changes Implemented

* Added a Mermaid diagram to the [README architecture overview](../../README.md#architecture-overview), with a link to the [detailed architecture](../ARCHITECTURE.md#1-near-term-scope).

## Key Decisions & Context

The summary highlights shared agent and MCP tools, live EDGAR requests, Gemini, and Cloud SQL filing indexes. A dashed edge marks the planned frontend API.

## Known Gotchas, Blockers & Environment Issues

The React Research page still uses mock data.

## Next Steps (Handoff Checklist)

* [ ] Update the frontend edge when the Python HTTP API is connected.
