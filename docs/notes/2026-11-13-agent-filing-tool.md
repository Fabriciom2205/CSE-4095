# Worklog: Agent Filing Tool Selection

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed

## Objective
Remove direct filing retrieval from the agent's available tools and direct disclosure research through RAG.

## Changes Implemented
* `python-brain/agent.py`: remove the filing-fetch tool from the model's tool list and specify the composite and follow-up tools in its instructions.
* `python-brain/test_research.py`: verify the available tools and instructions.

## Key Decisions & Context
The MCP filing-fetch tool and existing agent re-export remain available to their direct callers. The model-facing follow-up tool is named `sec_query_filing_rag`.

## Known Gotchas, Blockers & Environment Issues
The offline research tests pass. Live model and SEC calls were not run.

## Next Steps (Handoff Checklist)
* [ ] Validate the research workflow with live SEC and Google Cloud access.
