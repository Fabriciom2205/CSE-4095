# Worklog: Backend test layout

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Make the backend directory easier to navigate and make the commands for local and live testing easy to find.

## Changes Implemented

* Moved Python discovery tests into [python-brain/tests/](../../python-brain/tests/) and corrected imports between test modules.
* Moved opt-in EDGAR and Gemini checks into [tests/live/](../../python-brain/tests/live/). Updated the MCP transport check to locate the server from its new directory.
* Documented the commands in [Local Setup](../LOCAL_SETUP.md#run-the-backend-tests) and repaired worklog links to moved tests.

## Key Decisions & Context

The test package supports `python -m unittest discover -s python-brain` from the repository root and `python -m unittest discover` from inside `python-brain/`. The API and CLI keep their existing launch paths and import layout.

All 104 Python tests passed from the repository root with disposable PostgreSQL, along with both SQL checks.

## Known Gotchas, Blockers & Environment Issues

Run the smoke checks by module name from `python-brain/`. Local MCP initialization and tool discovery were verified over stdio and streamable HTTP. Live EDGAR and Gemini calls were outside this check.

## Next Steps (Handoff Checklist)

* [ ] Use the documented test commands when adding backend modules.
