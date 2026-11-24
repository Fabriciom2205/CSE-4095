# Worklog: Agent PostgreSQL readiness check

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed locally, with Cloud SQL setup pending

## Objective

Verify the shared agent and MCP PostgreSQL filing retrieval path with one command.

## Changes Implemented

* [Health check](../../python-brain/init.py) runs read-only filing index and vector queries when a reader is configured. The optional `--postgres TICKER` check requires a PostgreSQL excerpt from a live 10-K.
* [Integration tests](../../python-brain/tests/test_filing_store.py) exercise the readiness check with the documented database grants.
* [PostgreSQL setup](../POSTGRESQL.md#enable-persistent-filing-retrieval) documents how to run the check and when it exercises the writer.

## Key Decisions & Context

The regular check avoids index publication. Selecting a ticker explicitly allows the shared filing tool to build an index on a cache miss. The future frontend can make research requests through a Python backend that owns the database credentials.

The live health check passed against disposable PostgreSQL 17 with pgvector, real SEC filings, and Gemini. It passed first with both roles on an empty index and again with only the reader on the stored index. The offline health check and all 22 filing store, research, and importer tests also passed.

## Known Gotchas, Blockers & Environment Issues

The configured Cloud SQL database responded to a read-only inspection. It lacked pgvector, both filing retrieval tables, and the index writer role. The workspace had neither filing retrieval DSN configured.

## Next Steps (Handoff Checklist)

* [ ] Confirm the target database and migration access, apply migration 002, and configure scoped runtime credentials.
* [ ] Run the ticker-based check against Cloud SQL with a cold index and verify reader-only reuse.
