# ADR 0003: Store SEC Research Data in PostgreSQL

* **Date:** 2026-11-17
* **Status:** Accepted
* **Authors / Agents:** Project contributors, Codex
* **Supersedes:** None

## 1. Context & Problem Statement

Company Facts currently come directly from SEC EDGAR and filing retrieval uses an in-memory index. Persistent research needs typed fact history, source citations, and traversal over corporate relationships and XBRL dimensions.

## 2. Decision

Use PostgreSQL 15+ and standard SQL. Keep consolidated XBRL in `sec.fact`, filing metadata and evidence text in `sec.filing` and `sec.chunk`, and relationships and dimensional observations in `sec.node` and `sec.triple`. A numeric edge links to its dimension context separately from its value. The chunk link must refer to the same accession as an LLM-extracted assertion. Readers use a filtered view that excludes all model-extracted assertions until a review workflow exists.

The initial importer runs separately from the agent and can load selected consolidated concepts and the latest 10-K auditor. Dates are filing-date cutoffs. Retain different values and series contexts instead of discarding them as duplicates. An ambiguous auditor day stays unresolved. A subsidiary traversal reports historical positive assertions through the cutoff because filing history alone does not establish continued ownership.

## 3. Alternatives Considered

* A generic graph for all SEC data would complicate typed financial arithmetic and document retrieval.
* A graph extension and ORM would add operational overhead for the current SQL queries.

## 4. Consequences & Trade-offs

* The core schema runs locally and on Cloud SQL without extensions. A separate migration role and database grants keep ingestion rights away from the agent.
* [Optional filing retrieval](../POSTGRESQL.md#enable-persistent-filing-retrieval) adds pgvector and a separate pair of derived tables. The agent can index files outside the imported SEC corpus using a dedicated writer with access limited to those tables.
* Historical auditor coverage, dimensional context parsing, other relationship loaders, review of model extractions, and agent reads of imported facts and relationships remain future work. Reassess covering and BRIN indexes with real query plans and filing-date distribution.
