# Worklog: SEC PostgreSQL Integration

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed

## Objective

Implement a PostgreSQL foundation for SEC research and document how to host and manage it on Google Cloud.

## Changes Implemented

* [Migration](../../db/migrations/001_sec.sql) separates flat facts, filing evidence, dimensional observations, and relationships. [Query examples](../../db/research.sql) cover auditors, subsidiary traversal, and segment revenue.
* [Standalone importer](../../python-brain/ingest_sec.py) loads selected Company Facts and optionally the latest 10-K auditor using the existing SEC client and PostgreSQL's `psql`.
* [ADR 0003](../decisions/0003-postgresql-sec-research.md) records the design. The [runbook](../POSTGRESQL.md) covers provisioning, permissions, migrations, and recovery.

## Key Decisions & Context

A numeric edge carries a separate dimension reference. Auditor comparisons use dated observations, and conflicting observations on the same day stay unresolved. Subsidiary traversal shows known historical assertions. A model-extracted assertion requires a same-filing chunk, and the reader view excludes these assertions pending evidence review.

## Known Gotchas, Blockers & Environment Issues

The migration checks and documented reader and writer grants passed on a disposable PostgreSQL 18.6 instance. An end-to-end fixture verified decimal precision, idempotent replay, and rollback on conflicting provenance. Python ingestion and existing research tests passed. Live SEC ingestion and Cloud SQL provisioning remain unverified. The agent still uses live SEC and in-memory filing retrieval.

## Next Steps (Handoff Checklist)

* [ ] Verify the importer on a small live SEC batch and load historical auditor observations.
* [ ] Add a dimensional XBRL loader that retains full context and accurate periods, then prioritize other relationship loaders by research demand.
* [ ] Connect approved research queries through the reader role when the stored corpus is ready.
