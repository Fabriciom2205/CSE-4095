# Worklog: Security and PostgreSQL release handoff

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Prepared for main

## Objective

Publish the accumulated Python research changes to main under the requested security and database commit.

## Changes Implemented

* The release includes the [agent and MCP security changes](2026-11-17-agent-security.md), [PostgreSQL filing retrieval](2026-11-17-postgresql-filing-retrieval.md), and [local setup guide](../LOCAL_SETUP.md).

## Key Decisions & Context

The feature branch extends main with the existing MCP test and React frontend commits. The release can be published as a fast-forward. Local credentials and workspace MCP settings stay outside the commit.

## Known Gotchas, Blockers & Environment Issues

The React Research page still uses mock data. Remote MCP authentication and Secret Manager deployment integration remain open.

## Next Steps (Handoff Checklist)

* [ ] Follow the active backlog for the frontend research API and deployment controls.
