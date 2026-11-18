# Worklog: PostgreSQL Filing Retrieval Plan

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Planned

## Objective

Persist the agent's SEC filing chunks and embeddings in PostgreSQL so research sessions can reuse them instead of rebuilding an in-memory index.

## Changes Implemented

* Recorded this plan for the next development session and linked it from [AGENTS.md](../../AGENTS.md). No retrieval code or database migrations were changed in this session.

## Key Decisions & Context

* The agent currently fetches filings, extracts and chunks sections, generates 1,536-dimensional embeddings, and searches a process-local index in [filing_rag.py](../../python-brain/filing_rag.py). A restart loses that index.
* The user reports having created the Cloud SQL database, applied [001_sec.sql](../../db/migrations/001_sec.sql), and successfully imported one company’s financial facts and auditor assertion. The separate importer does not feed the current agent.
* The existing `sec.chunk` table stores filing text but has no vector or retrieval-version metadata. Add a **new migration**, preserving the applied schema and existing data.
* Use Cloud SQL's pgvector support for embeddings. Retain accession, section, chunk order, embedding model and dimensions, and chunking/version information so incompatible indexes are not mixed. Keep filing content and tool results marked as untrusted.
* On a research request, resolve the filing and check for a completed matching index. If present, embed the question and search stored vectors. If absent, fetch, chunk, and embed the filing, then publish the complete index atomically before searching it.
* Make concurrent first requests and retries safe. Avoid duplicate complete indexes and do not expose partial work as complete. Report database or embedding failures clearly.
* Separate database search privileges from index-building writes. Review MCP tool annotations and descriptions if a tool can cause writes. Keep the agent and MCP paths consistent.
* Start with accurate retrieval for a filing and section. Measure latency, storage, embedding cost and retrieval quality before choosing an approximate vector index.
* Connecting the agent to consolidated `sec.fact` records is a separate follow-up from persistent filing retrieval.

## Known Gotchas, Blockers & Environment Issues

* The user has a Cloud SQL instance and a working proxy-based importer setup. Do not require credentials or passwords in notes or commits.
* pgvector and a new migration have not been installed or applied for this plan. The exact embedding dimension was not verified against a live response in the prior test.
* Cloud SQL availability becomes a retrieval dependency. Consider connection management, least privilege, network access, and backups when implementing.
* Existing retrieval callers, MCP interfaces, tests, and structured untrusted-data envelopes must continue to work. The live agent test does not validate persistence, concurrent indexing, or MCP transport behavior.

## Next Steps (Handoff Checklist)

* [ ] Review the security, reliability and operational guidance relevant to the database change and record consequential design choices.
* [ ] Design and apply a versioned migration for persistent retrieval and pgvector without altering or deleting the user's existing data.
* [ ] Implement database-backed filing indexing and search for the agent and MCP tools, with separate read and write access and safe concurrent indexing.
* [ ] Test first indexing, reuse across process restarts, citations and section isolation, concurrent requests, partial failures, and unchanged prompt-injection boundaries.
* [ ] Run a small live validation against the user's configured database and SEC data when access is available. Document setup and measured costs.
