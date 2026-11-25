# Worklog: Ranked strategy replays and asset period returns

* **Date:** 2026-11-25
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Add ranked research strategies to the backtest engine and frontend. Match stock price changes to the selected chart period.

## Changes Implemented

* [Strategy parameters](../../python-brain/strategy.py) retain moving average as the default and add monthly momentum, quality and value, and momentum plus sentiment.
* [Historical signals](../../python-brain/strategy_data.py) use annual SEC facts filed before the decision day and prior Massive news labels. The [replay](../../python-brain/backtest.py) rebalances ranked strategies using next-open fills. Its API returns traded value relative to starting cash and a fixed-universe equal-weight buy-and-hold comparison.
* [Frontend](../../frontend/src/App.tsx) exposes strategy selection, saves the parameters in browser drafts, sends the chosen strategy to Phil for draft discussion, and renders the replay comparison. Asset changes now use the first and last closes in the selected range.

## Key Decisions & Context

* New strategies are historical simulations. Ranking ties use symbol order. Missing signals exclude the affected symbol from ranking. A strategy waits for enough eligible symbols to form the requested basket.
* The comparison uses whole shares at the first session's open and carries unspent cash. Neither side models fees, slippage, cash dividends, or share count changes.
* Simulated checks confirmed decision data timing, next-open fills, and the comparison. All four strategy types returned HTTP 200 through the local API. The live sentiment check used one symbol to stay within the provider quota.

## Known Gotchas, Blockers & Environment Issues

* Historical sentiment uses publication date as a proxy for label availability and excludes publication on the decision date. It cannot establish when a label first appeared in the feed.
* Massive rate limited consecutive replay requests. Broad universes and repeated captures can exceed the provider quota.
* Older bar-only snapshots can still replay price strategies. Quality/value and sentiment need the additional captured data.

## Next Steps (Handoff Checklist)

* [ ] Capture observed news arrival and labels if sentiment is evaluated as a strict point-in-time signal.
