# Worklog: MCP Transport Error Test

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Changed; live verification pending

## Objective
Fix the transport test's dependence on an SEC request returning HTTP 404.

## Changes Implemented
* `python-brain/test_mcp_server.py`: check a deterministic tool validation error through both transports instead of expecting a particular SEC response.

## Key Decisions & Context
The existing `test_mcp_error_includes_http_status` separately checks HTTP 404 formatting with a mocked response. The original failure did not display the actual SEC error.

## Known Gotchas, Blockers & Environment Issues
The 10 offline research tests pass. Transport checks hung in this environment, including a check without a live SEC request; the full live suite was not verified.

## Next Steps (Handoff Checklist)
* [x] Verify the live MCP smoke checks with SEC and Google Cloud access. [Verification](2026-11-24-backend-deliverables.md)
