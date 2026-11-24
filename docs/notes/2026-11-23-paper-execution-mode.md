# Worklog: Opt-in paper execution mode

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Implemented and tested with mocked submissions

## Objective

Keep proposals read only by default and let a trusted local caller authorize a paper order outside the conversation.

## Changes Implemented

* [portfolio_agent.py](../../python-brain/portfolio_agent.py) adds the CLI flag, scopes the run to one user-selected symbol and at most one order, and evaluates fresh positions, cash, quote, and limits before submission.
* [alpaca_client.py](../../python-brain/alpaca_client.py) adds a paper-only POST transport. It does not follow redirects or retry when the outcome is uncertain.
* Amended [ADR 0004](../decisions/0004-portfolio-and-deterministic-strategy.md#paper-execution-amendment) and documented both [modes](../LOCAL_SETUP.md#proposal-and-paper-execution-modes).

## Key Decisions & Context

The model still produces target weights. The backend derives and submits an order only in the user-authorized branch. Local runs are serialized and the broker must show no open order before execution. Only whole-share US equity day limit orders during regular hours are supported.

## Known Gotchas, Blockers & Environment Issues

All 74 Python tests passed with pgvector enabled, along with both SQL test scripts. Broker submissions were mocked. Live read-only asset and clock checks passed. Existing orders and other writers are external to the local lock. A run ending or switching back to proposal mode does not cancel an accepted order.

## Next Steps (Handoff Checklist)

* [ ] Verify an actual paper submission in a user-authorized execution run when desired.
