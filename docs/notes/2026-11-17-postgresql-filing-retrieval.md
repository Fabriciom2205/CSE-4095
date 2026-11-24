# Worklog: PostgreSQL Filing Retrieval

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed

## Objective

Implement the [retrieval plan](2026-11-17-postgresql-retrieval-plan.md) so agent and MCP filing research can reuse persisted SEC excerpts and embeddings.

## Changes Implemented

* [Migration 002](../../db/migrations/002_filing_retrieval.sql) adds pgvector and versioned filing retrieval tables.
* [Filing store](../../python-brain/filing_store.py) publishes an entire index in one transaction and searches it with exact cosine similarity.
* [Filing RAG](../../python-brain/filing_rag.py) uses the database when configured. It checks the stored index before downloading a filing and validates all 1,536-dimensional vectors before use.
* [MCP tools](../../python-brain/mcp_server.py) describe conditional index writes and retain the explicit untrusted-data envelope. [Setup](../POSTGRESQL.md#enable-persistent-filing-retrieval) documents the reader and index writer grants.
* [Integration tests](../../python-brain/tests/test_filing_store.py) verify reuse, citations, section isolation, concurrency, partial-write rollback, and embedding failure.

## Key Decisions & Context

Derived indexes use separate tables so the original SEC importer and evidence references can run independently. The retrieval key includes CIK, accession, filename, section, model, dimensions, and chunking version. Separate grants restrict the reader to searching and the index writer to publishing. Transactions run after SEC downloads and document embedding calls, which keeps database transactions short.

Both migrations, the documented role grants, the existing SEC schema checks, and the integration tests passed on disposable PostgreSQL 17 with pgvector. The Python research and importer regressions, offline health check, and both MCP transport handshakes also passed.

Live EDGAR and Gemini verification used the Business section of a Form 10-K. The first search took 5.30 seconds and made 14 embedding calls for 13 chunks and one question. A fresh reader-only process searched the persisted index in 2.24 seconds with one embedding call and no filing download. PostgreSQL reported 79,924 bytes of vector data and 22,318 bytes of text before relation overhead. These are single-run measurements on the disposable database.

## Known Gotchas, Blockers & Environment Issues

The configured Cloud SQL database was reachable and reported pgvector availability. Migration 002 and the role grants were exercised on the disposable instance. The Cloud SQL activation and verification are pending. Concurrent first requests can repeat embedding work before one transaction publishes the index. Section extraction retains the existing fallback to broader filing text when headings cannot be matched.

## Next Steps (Handoff Checklist)

* [ ] Apply migration 002 and grant the reader and index writer roles on Cloud SQL.
* [ ] Check cold and warm retrieval against Cloud SQL and measure retrieval quality and costs across more filings.
* [ ] Evaluate consolidated fact reads separately.
