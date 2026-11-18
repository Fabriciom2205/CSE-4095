# Worklog: Agent Retrieval Fix

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Implemented and live-tested

## Objective
Reduce research tool calls and identify why retrieval returned unrelated excerpts.

## Changes Implemented
* `python-brain/agent.py`: expose three ticker-first tools, cache identical calls per chat, and configure low thinking and a 20-call ceiling.
* `python-brain/sec_client.py` and `python-brain/mcp_server.py`: resolve exact tickers, reject unknown companies, and select the latest 10-K or 10-Q while retaining existing MCP filing parameters.
* `python-brain/filing_rag.py`: embed each text separately, with four concurrent requests, and reject unexpected embedding counts.
* `python-brain/test_research.py`: cover schemas, ticker tools, per-chat memoization, filing forms, and embedding cardinality and order.

## Key Decisions & Context
The baseline NVDA run used the composite tool first, followed by repeated RAG and full-text searches, reaching the 10-call limit. The root retrieval defect was embedding 99 chunks as one aggregate vector, which selected the first chunk instead of searching the whole index. Vertex's Gemini Embedding 2 endpoint accepts one Content per request; explicit separate Content objects were rejected by the installed SDK.

## Validation
Live retrieval returned 99 vectors for 99 NVIDIA risk chunks and retrieved a Taiwan-specific passage. The revised live NVDA chat answered in 38 seconds with two tool calls. Fifteen offline research tests pass.

## Next Steps (Handoff Checklist)
* [ ] Evaluate retrieval and citations across more filings and questions.
* [ ] Assess persistent indexes and SEC response caching; separate embedding requests increase first-index API calls and cost.
