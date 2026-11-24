# Worklog: Portfolio, risk, and strategy replay

* **Date:** 2026-11-20
* **Contributor / Agent:** Codex and three subagents
* **Branch:** fabricio/market-data-apis
* **Status:** Implemented and verified with disposable PostgreSQL and offline vendor fixtures

## Objective

Add read-only brokerage access, deterministic portfolio risk, and a reproducible strategy replay without coupling these functions to the research agent.

## Changes Implemented

* Added the [Alpaca client](../../python-brain/alpaca_client.py) for accounts, open positions, and a bounded order page. The [portfolio migration](../../db/migrations/003_portfolio.sql) defines accounts, positions, execution fills, and risk limits.
* Added [risk functions](../../python-brain/risk.py) and boundary tests. The concentration and drawdown checks use exact arithmetic for limit comparisons and require positive equity where used as a denominator.
* Added [strategy data](../../python-brain/strategy.py) and a [replay CLI](../../python-brain/backtest.py). It sizes positions at the close, fills at the next open, and can replay a saved snapshot without external calls. A synthetic 12-month fixture produced identical CLI results twice: 261 sessions, 8 fills, final equity 8460 from 10000, and maximum drawdown 0.154.
* Applied migrations 001–003 to a disposable PostgreSQL instance with pgvector. Both SQL test files, Python discovery with the pgvector integration tests enabled, the live SEC/MCP self-checks, and the offline health check passed.

## Key Decisions & Context

* [ADR 0004](../decisions/0004-portfolio-and-deterministic-strategy.md) records the boundaries. The current agent is unchanged. Broker data remains inside the portfolio backend and the client uses GET requests only.
* Keep replay reproducible through a fixed universe and saved raw bar snapshot. The simulator rejects share-count changes detected during capture. Current replay uses daily prices and does not model dividends, fees, or slippage.

## Known Gotchas, Blockers & Environment Issues

* The local environment had no Alpaca or Massive credentials. Client authentication and live Massive capture were not exercised. Alpaca payload and Massive query handling were tested offline.
* Migration 003 was applied only to disposable PostgreSQL. Broker reads do not automatically persist account or position data.

## Next Steps (Handoff Checklist)

* [ ] Verify a paper account and capture a live 12-month Massive snapshot with configured keys.
* [ ] Define brokerage sync and scoped portfolio database grants if persistent snapshots are needed.
