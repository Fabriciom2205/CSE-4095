# Worklog: Agent and Cloud SQL smoke commands

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Complete

## Objective

Provide commands to ask the agent a real filing question and verify Cloud SQL independently.

## Changes Implemented

* Confirmed the [agent constructor](../../python-brain/agent.py) for the prompt command and the [PostgreSQL health check](../../python-brain/init.py) for reader-only verification.

## Key Decisions & Context

The agent prompt tests the natural-language flow. From the repository root, `SEC_RAG_WRITE_DSN='' python python-brain/init.py --postgres MSFT` requires a stored filing excerpt while disabling index publication for that run.

## Known Gotchas, Blockers & Environment Issues

The proxy must be running. Reader-only retrieval requires an existing index. The [migration verification](2026-11-17-cloud-sql-filing-retrieval.md) populated the MSFT Business section and confirmed reader-only reuse.

## Next Steps (Handoff Checklist)

* [ ] Configure Secret Manager references when deploying the backend.
