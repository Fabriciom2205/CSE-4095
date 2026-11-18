# Worklog: Filing Retrieval Noise

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Fixed; live verification pending

## Objective
Address noisy filing excerpts observed during live SEC research.

## Changes Implemented
* `python-brain/filing_rag.py`: reject unknown sections before fetching and omit inline XBRL headers and display-none content when chunking.
* `python-brain/mcp_server.py` and `python-brain/agent.py`: clarify accepted section names and ask the agent to answer once it has relevant evidence.
* `python-brain/test_research.py`: cover hidden metadata removal and invalid section rejection.

## Key Decisions & Context
The observed `part1item1` section was unsupported and silently fell back to the complete filing, including hidden XBRL metadata.

## Known Gotchas, Blockers & Environment Issues
Twelve offline research tests pass. The live model workflow remains unverified; instructions alone do not guarantee a response before the SDK call limit.

## Next Steps (Handoff Checklist)
* [ ] Retry the research prompt against a live SEC filing and inspect results if the model still loops.
