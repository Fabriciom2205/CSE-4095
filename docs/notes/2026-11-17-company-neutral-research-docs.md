# Worklog: Company-Neutral Research Documentation

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed

## Objective

Describe the research workflow independently of the issuer used for live verification.

## Changes Implemented

* [Live SEC research note](2026-11-17-live-sec-research.md) uses a caller-selected ticker and preserves the verification outcome. Earlier notes retain their findings and measurements in issuer-neutral language.
* [PostgreSQL setup](../POSTGRESQL.md) prompts for the issuer in its importer examples. The [MCP lookup description](../../python-brain/mcp_server.py) and [Research page](../../frontend/src/pages/Research.tsx) use general search copy.
* [AGENTS.md](../../AGENTS.md) links the renamed note and uses issuer-neutral backlog wording.

## Key Decisions & Context

The agent and importer resolve caller-provided tickers. Fixed issuer identifiers in live connectivity checks and test fixtures provide reproducible test inputs. The frontend sample portfolio has multiple issuers.

## Known Gotchas, Blockers & Environment Issues

The retained live timings describe a single-filing sample.

## Next Steps (Handoff Checklist)

* [ ] Use multiple issuers when evaluating filing coverage or reporting representative retrieval timings.
