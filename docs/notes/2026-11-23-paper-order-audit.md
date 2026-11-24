# Worklog: Phase 6 paper order audit and reconciliation

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Implemented and verified against disposable PostgreSQL

## Objective

Make paper submissions safe to reconcile after a crash and make their controls and fills auditable.

## Changes Implemented

* [Migration 004](../../db/migrations/004_portfolio_audit.sql) adds decisions, stable retry bindings, equity observations, and daily limits.
* [Portfolio ledger](../../python-brain/portfolio_store.py) commits the SHA-256-derived client ID before submission. A PostgreSQL account lock serializes cooperative runners, and unresolved intents and daily caps prevent additional submissions.
* [CLI](../../python-brain/portfolio_agent.py) uses stored limits and peak equity for execution. It adds a launch-time halt flag, a stable decision key, and separate equity recording and reconciliation commands. The HTTP API stays free of execution routes.
* All 91 Python tests and both SQL scripts passed. Tests cover duplicate submissions, crashes on both sides of submission, timeout ambiguity, stored drawdown, separate daily caps, account locking, and fill reconciliation.

## Key Decisions & Context

A stable operator key binds the request before a retry can generate a different proposal. Equal decisions share the same client order ID even across different keys. Orders are taken from broker state, and fills are written from individual FILL activities. The daily cap charges reserved attempts at their limit price in New York calendar days.

## Known Gotchas, Blockers & Environment Issues

Live GET checks matched an existing paper order's fill activity totals. No execution DSN is configured and the market was closed, so no new paper order was issued. Sector caps fail explicitly without a sector source. Accepted orders must be canceled in Alpaca if needed.

## Next Steps (Handoff Checklist)

* [ ] Apply migration 004 to the intended execution database, grant the runner role, and seed trusted history and caps.
* [ ] During regular hours submit one authorized paper decision, rerun its same key, and reconcile fills. See the [runbook](../LOCAL_SETUP.md#audited-paper-execution-runbook).
