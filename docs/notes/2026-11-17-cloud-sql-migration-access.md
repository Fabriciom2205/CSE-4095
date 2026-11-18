# Worklog: Cloud SQL migration access and runtime credentials

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Blocked on a migration administrator login

## Objective

Apply the filing retrieval migration and scoped grants to the confirmed project database, and document Secret Manager for the backend credentials.

## Changes Implemented

* [PostgreSQL setup](../POSTGRESQL.md#runtime-credentials-in-secret-manager) documents separate, versioned Secret Manager references for the reader and the index writer.

## Key Decisions & Context

The project database is `monroe_fund` on Cloud SQL instance `mfund-instance`. The local Cloud SQL Auth Proxy is reachable. Read-only checks confirmed that pgvector is available, the retrieval tables and writer role are absent, and the reader role exists.

## Known Gotchas, Blockers & Environment Issues

The configured `sec_writer` login lacks database and schema creation privileges and cannot create roles. Libpq found the new `postgres` entry in the mode-0600 password file, and Cloud SQL rejected the password. Catalog checks also showed that `postgres` lacks CREATE on the `sec` schema. The schema owner, `quickstart-user`, has database CREATE, CREATEROLE, and Cloud SQL administrative membership. Its password is missing from the local password file. The Secret Manager API is disabled in the project. No database or Google Cloud configuration was changed.

## Next Steps (Handoff Checklist)

* [ ] Supply the `quickstart-user` credential through a protected libpq password file, then apply migration 002 and the grants.
* [ ] Provision a password for `sec_index_writer` and configure both runtime DSNs. Enable Secret Manager when using it to supply backend credentials.
* [ ] Run a cold filing retrieval, then verify reader-only reuse through the agent health check.
