# Worklog: Agent latency and model usage review

* **Date:** 2026-11-23
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Reduce model and provider work in the current research and proposal agents while preserving cited evidence, streaming, and deterministic portfolio checks.

## Changes Implemented

* [ADK runtime](../../python-brain/adk_runtime.py) gives the coordinator direct tools for individual lookups and keeps specialists for comparisons. A shared model instance enforces 12 model calls per run. The `adk_runtime` logger emits an INFO record with generation calls, elapsed time, and provider input, cached, output, and thinking token counts. Session checks and citation state reads skip event history. Compaction triggers on prompt size.
* [HTTP proposals](../../python-brain/api.py) check portfolio availability before spending on evidence or model calls. The runtime permits three simultaneous proposal evidence reads per process and fetches quotes once filings are ready. The final exposure check reads through the existing portfolio cache.
* [SEC retrieval](../../python-brain/filing_rag.py) coalesces concurrent builds for the same filing index in each worker. [CIK lookup](../../python-brain/sec_client.py) initializes the ticker map once under concurrent load.
* [Gemini SDK agent](../../python-brain/agent.py) refreshes market data tool calls within a chat and shares a single in-model portfolio read between snapshot and validation. Final proposal validation reads current portfolio state.

## Key Decisions & Context

Kept the current Gemini Flash model and ADK sessions. A live NVDA quote returned the same price and timestamp in fresh conversations before and after the change. Calls dropped from four to two and elapsed time from 8.92 to 4.44 seconds. Input tokens went from 829 to 942. Generated tokens including thinking fell from 394 to 104. A live Berkshire 13F comparison streamed in 6.96 seconds with two calls and citations to both filings. The authenticated NVDA proposal returned a valid target in 18.56 seconds with 4.38 seconds in the single generation turn. That smoke test used an empty in-memory SEC filing cache.

All 104 Python discovery tests and both PostgreSQL SQL checks passed.

## Known Gotchas, Blockers & Environment Issues

Live latency varies across provider requests. Generation metrics cover Gemini responses with provider usage metadata. The proposal logs also record filing and quote elapsed time. Embedding charges and dollar totals are outside these logs. The filing build lock is process-local, so separate workers can still build the same cold index.

## Next Steps (Handoff Checklist)

* [ ] Build a representative benchmark set for finding quality, latency, and generation and embedding costs across warm and cold retrieval.
