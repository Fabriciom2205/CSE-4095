# Worklog: Google Cloud ADC for Python Brain

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed

## Objective
Use Google Cloud Application Default Credentials for agent and embedding calls.

## Changes Implemented
* Added `python-brain/google_client.py` and switched agent, MCP RAG, and health checks to Cloud clients using API v1.
* Set the agent model to `gemini-3.8-flash` and updated configuration, documentation, and offline tests.

## Key Decisions & Context
* Project and location are passed explicitly so legacy API key variables cannot override ADC.

## Known Gotchas, Blockers & Environment Issues
* The local `.env` has no Cloud project configured. Offline checks passed with a dummy project; live Cloud and SEC calls were not run.

## Next Steps (Handoff Checklist)
* [ ] Configure the Cloud project and ADC, then run `python python-brain/init.py` to verify live access and embeddings.
