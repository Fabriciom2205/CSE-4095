# Worklog: Agent Client Lifetime

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Fixed; live verification pending

## Objective
Fix the closed-client error when sending a message through a newly created SEC agent.

## Changes Implemented
* `python-brain/agent.py`: retain the Google SDK client for the lifetime of the returned chat.
* `python-brain/test_research.py`: verify the client remains open while the chat is alive and can be collected afterward.

## Key Decisions & Context
The SDK client closes its HTTP client on destruction; its chat keeps the models module, but not the owning client.

## Known Gotchas, Blockers & Environment Issues
The 11 offline research tests pass. The live Google and SEC workflow was not run in this restricted environment.

## Next Steps (Handoff Checklist)
* [ ] Retry a 10-K research request with live credentials and SEC access.
