# Worklog: Embeddings and Research Tools

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Code complete; live embedding verification pending

## Objective
Use 1536-dimensional embeddings and share SEC tool wrappers.

## Changes Implemented
* `python-brain/filing_rag.py`, `python-brain/init.py`, `.env.example`: request and check 1536-dimensional vectors and remove the incompatible 768-dimensional fallback.
* `python-brain/agent.py`: use the MCP tool functions directly, including the composite research tool and bounded filing excerpts.
* `python-brain/test_research.py`: cover shared tools, embedding configuration, errors, and health-check dimensions.

## Key Decisions & Context
Different embedding models do not share a vector space; switching silently between them is unsafe. Cached embeddings are in memory and are rebuilt on process restart.

## Known Gotchas, Blockers & Environment Issues
Ten offline tests, Gemini tool schema conversion, and the offline health check passed. Network restrictions prevented live embedding requests.

## Next Steps (Handoff Checklist)
* [ ] Run the live health check and evaluate retrieval quality with 1536-dimensional embeddings.
