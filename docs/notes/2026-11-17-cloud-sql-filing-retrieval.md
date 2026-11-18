# Worklog: Cloud SQL filing retrieval migration

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Complete

## Objective

Enable the shared agent and MCP PostgreSQL filing retrieval path on the project Cloud SQL database.

## Changes Implemented

* Applied [migration 002](../../db/migrations/002_filing_retrieval.sql) on `monroe_fund` with the schema owner. Pgvector 0.8.7, both retrieval tables, and the scoped reader and index writer grants committed in one transaction.
* Created `sec_index_writer` and added its generated password to the protected local libpq password file.
* Configured the ignored local `.env` with both runtime DSNs. The credentials are read from the local libpq password file.

## Key Decisions & Context

Catalog checks confirmed that the reader can select from both retrieval tables and lacks INSERT on them. The writer can insert into both tables and read the index ID column. A connection as the writer successfully inserted an index and a vector, then rolled back the test rows.

## Known Gotchas, Blockers & Environment Issues

After the reader credential became available, the writer entry was missing from the password file. The newly created writer password was regenerated and its entry restored. A live agent filing check published the Business-section index for a real 10-K to Cloud SQL and the reader-only run retrieved the stored excerpt. Secret Manager setup remains a deployment task.

## Next Steps (Handoff Checklist)

* [ ] Configure versioned [Secret Manager credentials](../POSTGRESQL.md#runtime-credentials-in-secret-manager) when deploying the backend.
