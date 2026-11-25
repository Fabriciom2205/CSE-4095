# Worklog: Phil chat contrast, research budget, and JavaScript bundles

* **Date:** 2026-11-24
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Restore readable messages and successful research replies in Phil and resolve the Vite chunk size warning.

## Changes Implemented

* [Chat styles](../../frontend/src/style.css) give the outgoing bubble the theme's primary text color on a muted surface, with a border to distinguish it from Phil's replies.
* [ADK runtime](../../python-brain/adk_runtime.py) disables further function calls after eight model calls so specialists and the coordinator have room to answer within the existing twelve call cap. The coordinator should summarize available evidence and identify gaps.
* [Vite configuration](../../frontend/vite.config.ts) splits React and its runtime dependencies into a separately cacheable file.

## Key Decisions & Context

* Local service logs showed a specialist exhausting the shared model budget after roughly 62 seconds. The research stream reported the exception as “Research unavailable.”
* A live three company SEC comparison completed against the restarted local API in 46 seconds with a final streamed answer and three citations. It used six model calls. A mocked provider check separately verified the function calling cutoff.
* The build completed without the size warning. The largest JavaScript chunk went from 695 kB to 475 kB before compression, with roughly the same total JavaScript on initial load.

## Known Gotchas, Blockers & Environment Issues

* Broad research may still take time or return a partial comparison when the tool budget is reached. The local smoke request completed before reaching that cutoff.
* Astryx doctor reported no failures and still reports a source style warning.

## Next Steps (Handoff Checklist)

* [ ] Measure latency and coverage on representative broad research prompts before changing the budget again.
