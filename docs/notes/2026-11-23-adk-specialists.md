# Worklog: ADK specialists and durable conversations

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Architecture proposal updated

## Objective

Evaluate specialist agents and conversation recovery across a service restart.

## Changes Implemented

Updated [ADR 0005](../decisions/0005-phase-5-api-and-agent-runtime.md) to propose ADK orchestration and PostgreSQL sessions behind the FastAPI domain API. The paper execution boundary is unchanged.

## Key Decisions & Context

Start with narrow SEC and market specialists and a private proposal workflow. Give the coordinator structured evidence and keep deterministic checks in Python. Persist conversation and proposal context without persisting execution opt-in.

## Known Gotchas, Blockers & Environment Issues

No compatibility spike or code migration has run. Delegation can add latency and increase token usage when handoffs repeat context.

## Next Steps (Handoff Checklist)

* [ ] Verify SEC citation and proposal parity with an ADK spike.
* [ ] Restart the service and prove a follow-up can recover its conversation.
