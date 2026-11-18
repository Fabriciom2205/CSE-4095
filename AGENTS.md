# Agent Operating Guidelines & Workspace Index

Welcome! If you are an AI coding assistant (or human developer) working on this repository, **read this file before beginning work.**

This repository is shared across multiple contributors and agentic workflows. To ensure seamless collaboration and uninterrupted context between sessions, follow the conventions outlined below.

---

## Project Overview

**The Monroe Fund** is a Python-first AI-assisted financial research project. Near-term work focuses on agentic search, MCP tools, SEC filings, and aggregation of financial data. The React frontend supports research but currently uses mock data. Persistent storage and Google Cloud infrastructure are planned as needed. Rust compute, backtesting, and execution components remain possible future work, but are deferred.
* **Architecture Reference:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
* **Architectural Decisions:** [ADR 0001](docs/decisions/0001-polyglot-trading-platform-architecture.md), revised by [ADR 0002](docs/decisions/0002-python-first-research-scope.md). [ADR 0003](docs/decisions/0003-postgresql-sec-research.md) records the SEC PostgreSQL design.
---

## Agent Workflow & Handoff Protocol

Every agent working on this repository must adhere to the following 3-step lifecycle:

```
[Start Session] ──> Check AGENTS.md & Latest Notes
       │
[Execute Work]  ──> Keep changes scoped & tested (NO UNREQUESTED CODE IMPLEMENTATION)
       │
[End Session]   ──> Create a Note in docs/notes/ & Update AGENTS.md
```

### 1. At the Start of Every Session
1. Read the **Active Tasks / Next Steps** section below.
2. Review the most recent note in [`docs/notes/`](docs/notes/) to understand recent changes, decisions, and known issues.
3. Verify git status and ensure you are working on the intended branch.

### Google Cloud Well-Architected Framework

Apply the [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework) to development and architecture decisions. Consider the six pillars in proportion to the change; read and apply the relevant project skills when designing, implementing, or reviewing work in their areas:

* [Operational excellence](.agents/skills/google-cloud-waf-operational-excellence/SKILL.md): delivery, monitoring, and incident response.
* [Security, privacy, and compliance](.agents/skills/google-cloud-waf-security/SKILL.md): identity, access, data protection, and auditability.
* [Reliability](.agents/skills/google-cloud-waf-reliability/SKILL.md): failure handling, recovery, and availability.
* [Cost optimization](.agents/skills/google-cloud-waf-cost-optimization/SKILL.md): resource usage and cost trade-offs.
* [Performance optimization](.agents/skills/google-cloud-waf-performance-optimization/SKILL.md): measurable latency, throughput, and capacity.
* [Sustainability](.agents/skills/google-cloud-waf-sustainability/SKILL.md): efficient resource use and environmental impact.

Use the [architecture guidance](docs/ARCHITECTURE.md#6-well-architected-development-guidance) to assess relevant trade-offs. Record consequential decisions and unresolved risks; do not claim planned controls are implemented. The skills are copied from [google/skills](https://github.com/google/skills) at commit `67c4dbc8ff6313ef117d938e53bb21315fc281ae` under the [Apache 2.0 license](.agents/skills/GOOGLE-SKILLS-LICENSE). Their attribution instructions apply to commands executed using the skills, subject to user preferences and higher-priority instructions.

### 2. When Proposing Major Architectural Changes
* For significant architectural, framework, or tooling choices, document the proposal as an **Architecture Decision Record (ADR)** in [`docs/decisions/`](docs/decisions/) following the [ADR Template](docs/decisions/TEMPLATE.md).

### 3. At the End of Every Session (Mandatory Handoff)
Before closing your turn or concluding a task:
1. **Create a worklog note** in `docs/notes/YYYY-MM-DD-<short-topic>.md` using the [Worklog Template](docs/notes/TEMPLATE.md).
2. **Link the new note** in the [Worklogs & Session History](#worklogs--session-history) table below.
3. **Update the [Active Tasks & Backlog](#active-tasks--backlog)** section below so the next agent knows what to pick up immediately.

---

## Active Tasks & Backlog

Use this checklist for handoffs between agents. Keep it up to date.

* [x] Document the active Python research workflow and defer Rust components in the [README](README.md), [architecture diagram](docs/ARCHITECTURE.md#1-near-term-scope), and [Python-first scope decision](docs/decisions/0002-python-first-research-scope.md)
* [x] Implement SEC EDGAR search and in-memory vector RAG agent in [python-brain/](python-brain/)
* [x] Configure environment variables (.env, .env.example) and update project branding to The Monroe Fund
* [x] Implement Model Context Protocol (MCP) server for SEC EDGAR tools in [python-brain/mcp_server.py](python-brain/mcp_server.py)
* [x] Complete codebase audit and refactoring (deduplicate RAG, fix search schema, connection pooling, bounded cache)
* [x] Add python-brain environment & health check script in [python-brain/init.py](python-brain/init.py)
* [x] Add end-to-end MCP server tests (tools, resource, prompt, stdio + streamable-http) in [python-brain/test_mcp_server.py](python-brain/test_mcp_server.py)
* [x] Fix MCP error messages, date filtering, oversized filing output, and section extraction; add composite research tool (see [docs/notes/2026-11-13-sec-research-improvements.md](docs/notes/2026-11-13-sec-research-improvements.md))
* [ ] Evaluate prompt-injection defenses with adversarial model tests; implement authentication and authorization before remote or multi-user MCP use (see [docs/notes/2026-11-17-agent-security.md](docs/notes/2026-11-17-agent-security.md))
* [ ] Verify SEC MCP and composite research against live filings and transports (see [docs/notes/2026-11-13-sec-research-improvements.md](docs/notes/2026-11-13-sec-research-improvements.md))
* [x] Retry live agent research after the client lifetime fix (see [docs/notes/2026-11-13-agent-client-lifetime.md](docs/notes/2026-11-13-agent-client-lifetime.md))
* [x] Retry live SEC research after filtering hidden XBRL and validating filing sections (see [docs/notes/2026-11-13-filing-retrieval-noise.md](docs/notes/2026-11-13-filing-retrieval-noise.md))
* [ ] Verify filing section extraction across more real filings; assess indexing cost and persistent storage (see [docs/notes/2026-11-13-agent-retrieval-fix.md](docs/notes/2026-11-13-agent-retrieval-fix.md))
* [ ] Re-run MCP transport tests with live SEC access after the deterministic error assertion fix (see [docs/notes/2026-11-13-mcp-transport-error-test.md](docs/notes/2026-11-13-mcp-transport-error-test.md))
* [ ] Make `test_cache_eviction_bounded` and `test_archive_url_construction` call the real `filing_rag` / `sec_client` code
* [x] Scaffold React + TypeScript frontend with mock data in [frontend/](frontend/) (see [docs/notes/2026-11-11-frontend-scaffold.md](docs/notes/2026-11-11-frontend-scaffold.md))
* [x] Adopt Private Ledger with translucent navigation and controls (see [docs/notes/2026-11-11-ui-style-mockups.md](docs/notes/2026-11-11-ui-style-mockups.md))
* [x] Verify live 1536-dimensional embeddings using a real SEC filing and pgvector (see [docs/notes/2026-11-17-postgresql-filing-retrieval.md](docs/notes/2026-11-17-postgresql-filing-retrieval.md))
* [ ] Add a python-brain HTTP API and wire the frontend Research page (`frontend/src/data/api.ts`) to it
* [ ] Add frontend tests (Vitest + Playwright smoke test) and ESLint
* [ ] Deferred: Initialize remaining workspace directories (rust-muscle, proto)
* [ ] Deferred: Set up protobuf/gRPC definitions if a Rust daemon is needed
* [ ] Deferred: Configure PyO3/maturin bindings if measured compute needs justify them
* [x] Add PostgreSQL schema, SEC fact and latest auditor import, and Cloud SQL guide ([setup](docs/POSTGRESQL.md))
* [ ] Verify the importer against live EDGAR and add dimensional XBRL and historical relationship loaders
* [x] Implement PostgreSQL-backed agent and MCP filing retrieval following [the retrieval plan](docs/notes/2026-11-17-postgresql-retrieval-plan.md)
* [x] Add a single-command PostgreSQL filing retrieval check for the agent and its shared MCP tool (see [setup](docs/POSTGRESQL.md#enable-persistent-filing-retrieval))
* [x] Apply migration 002 and scoped database grants to Cloud SQL (see [verification](docs/notes/2026-11-17-cloud-sql-filing-retrieval.md))
* [x] Configure local Cloud SQL runtime DSNs and verify both cold indexing and reader-only reuse with `python python-brain/init.py --postgres TICKER` (see [verification](docs/notes/2026-11-17-cloud-sql-filing-retrieval.md) and [smoke commands](docs/notes/2026-11-17-agent-smoke-commands.md))
* [x] Document local backend and Cloud SQL setup, password-file configuration, and 10-Q verification in [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md)
* [ ] Configure Secret Manager references for the database roles when deploying the backend (see [setup](docs/POSTGRESQL.md#runtime-credentials-in-secret-manager))
* [x] Prepare the shared security and PostgreSQL changes for the main branch (see [release handoff](docs/notes/2026-11-17-security-postgresql-release.md))
* [ ] Evaluate PostgreSQL reads for consolidated financial facts
* [ ] Set up Python service deployment and CI/CD when needed, applying Well-Architected guidance and documenting unmet controls

---

## Worklogs & Session History

Keep a reverse-chronological list of session notes here. Whenever you create a note in `docs/notes/`, add a row below:

| Date | Topic / Session | Note Link | Contributors / Agent |
| :--- | :--- | :--- | :--- |
| 2026-11-17 | Security and PostgreSQL release handoff | [docs/notes/2026-11-17-security-postgresql-release.md](docs/notes/2026-11-17-security-postgresql-release.md) | Codex |
| 2026-11-17 | Local backend and Cloud SQL setup guide | [docs/notes/2026-11-17-local-cloud-sql-setup-guide.md](docs/notes/2026-11-17-local-cloud-sql-setup-guide.md) | Codex |
| 2026-11-17 | Python research architecture documentation | [docs/notes/2026-11-17-python-research-architecture-docs.md](docs/notes/2026-11-17-python-research-architecture-docs.md) | Codex |
| 2026-11-17 | Agent and Cloud SQL smoke commands | [docs/notes/2026-11-17-agent-smoke-commands.md](docs/notes/2026-11-17-agent-smoke-commands.md) | Codex |
| 2026-11-17 | Cloud SQL filing retrieval migration | [docs/notes/2026-11-17-cloud-sql-filing-retrieval.md](docs/notes/2026-11-17-cloud-sql-filing-retrieval.md) | Codex |
| 2026-11-17 | Cloud SQL migration access and runtime credentials | [docs/notes/2026-11-17-cloud-sql-migration-access.md](docs/notes/2026-11-17-cloud-sql-migration-access.md) | Codex |
| 2026-11-17 | Agent PostgreSQL readiness check | [docs/notes/2026-11-17-postgresql-readiness.md](docs/notes/2026-11-17-postgresql-readiness.md) | Codex |
| 2026-11-17 | Company-neutral research documentation | [docs/notes/2026-11-17-company-neutral-research-docs.md](docs/notes/2026-11-17-company-neutral-research-docs.md) | Codex |
| 2026-11-17 | PostgreSQL filing retrieval implementation | [docs/notes/2026-11-17-postgresql-filing-retrieval.md](docs/notes/2026-11-17-postgresql-filing-retrieval.md) | Codex |
| 2026-11-17 | PostgreSQL filing retrieval plan | [docs/notes/2026-11-17-postgresql-retrieval-plan.md](docs/notes/2026-11-17-postgresql-retrieval-plan.md) | Codex |
| 2026-11-17 | Live SEC research test | [docs/notes/2026-11-17-live-sec-research.md](docs/notes/2026-11-17-live-sec-research.md) | Codex |
| 2026-11-17 | SEC PostgreSQL integration | [docs/notes/2026-11-17-sec-postgresql.md](docs/notes/2026-11-17-sec-postgresql.md) | Codex |
| 2026-11-17 | Agent and MCP security | [docs/notes/2026-11-17-agent-security.md](docs/notes/2026-11-17-agent-security.md) | Codex |
| 2026-11-16 | Python-first research scope | [docs/notes/2026-11-16-python-first-research-scope.md](docs/notes/2026-11-16-python-first-research-scope.md) | Codex |
| 2026-11-13 | Well-Architected guidance | [docs/notes/2026-11-13-well-architected-guidance.md](docs/notes/2026-11-13-well-architected-guidance.md) | Codex |
| 2026-11-13 | Documentation cleanup | [docs/notes/2026-11-13-documentation-cleanup.md](docs/notes/2026-11-13-documentation-cleanup.md) | Codex |
| 2026-11-13 | Agent retrieval fix | [docs/notes/2026-11-13-agent-retrieval-fix.md](docs/notes/2026-11-13-agent-retrieval-fix.md) | Codex |
| 2026-11-13 | Agent loop review | [docs/notes/2026-11-13-agent-loop-review.md](docs/notes/2026-11-13-agent-loop-review.md) | Codex |
| 2026-11-13 | Filing retrieval noise | [docs/notes/2026-11-13-filing-retrieval-noise.md](docs/notes/2026-11-13-filing-retrieval-noise.md) | Codex |
| 2026-11-13 | Agent client lifetime | [docs/notes/2026-11-13-agent-client-lifetime.md](docs/notes/2026-11-13-agent-client-lifetime.md) | Codex |
| 2026-11-13 | MCP transport error test | [docs/notes/2026-11-13-mcp-transport-error-test.md](docs/notes/2026-11-13-mcp-transport-error-test.md) | Codex |
| 2026-11-13 | Agent filing tool selection | [docs/notes/2026-11-13-agent-filing-tool.md](docs/notes/2026-11-13-agent-filing-tool.md) | Codex |
| 2026-11-13 | Embeddings and research tools | [docs/notes/2026-11-13-cloud-mcp-embeddings.md](docs/notes/2026-11-13-cloud-mcp-embeddings.md) | Codex |
| 2026-11-13 | SEC research improvements | [docs/notes/2026-11-13-sec-research-improvements.md](docs/notes/2026-11-13-sec-research-improvements.md) | Codex |
| 2026-11-13 | Google Cloud ADC for Python Brain | [docs/notes/2026-11-13-google-cloud-adc.md](docs/notes/2026-11-13-google-cloud-adc.md) | Codex |
| 2026-11-11 | Live SEC Testing for MCP Server & Agent | [docs/notes/2026-11-11-live-mcp-and-agent-sec-testing.md](docs/notes/2026-11-11-live-mcp-and-agent-sec-testing.md) | Antigravity |
| 2026-11-11 | UI Restyle: Ledger + Glass (from Ledger/Brutalist mockups) | [docs/notes/2026-11-11-ui-style-mockups.md](docs/notes/2026-11-11-ui-style-mockups.md) | Claude Code |
| 2026-11-11 | Frontend Scaffold (React + TS, mock data) | [docs/notes/2026-11-11-frontend-scaffold.md](docs/notes/2026-11-11-frontend-scaffold.md) | Claude Code |
| 2026-11-09 | SEC EDGAR MCP Server Testing | [docs/notes/2026-11-09-mcp-server-testing.md](docs/notes/2026-11-09-mcp-server-testing.md) | Fabricio |
| 2026-11-09 | Python Brain Health Check (init.py) | [docs/notes/2026-11-09-python-brain-health-check.md](docs/notes/2026-11-09-python-brain-health-check.md) | Fabricio |
| 2026-11-09 | Codebase Audit & Refactoring | [docs/notes/2026-11-09-codebase-audit-and-refactor.md](docs/notes/2026-11-09-codebase-audit-and-refactor.md) | Antigravity |
| 2026-11-09 | SEC EDGAR MCP Server Implementation | [docs/notes/2026-11-09-mcp-server-implementation.md](docs/notes/2026-11-09-mcp-server-implementation.md) | Antigravity |
| 2026-11-09 | The Monroe Fund Branding & Environment Setup | [docs/notes/2026-11-09-monroe-fund-branding-and-env-configuration.md](docs/notes/2026-11-09-monroe-fund-branding-and-env-configuration.md) | Antigravity |
| 2026-11-08 | Section Targeting & Batch Embedding Optimization | [docs/notes/2026-11-08-section-targeting-and-batch-embedding.md](docs/notes/2026-11-08-section-targeting-and-batch-embedding.md) | Antigravity |
| 2026-11-07 | SEC Search & RAG Agent Implementation | [docs/notes/2026-11-07-sec-agent-rag-implementation.md](docs/notes/2026-11-07-sec-agent-rag-implementation.md) | Antigravity |
| 2026-11-07 | Polyglot Architecture & Specifications Documentation | [docs/notes/2026-11-07-architecture-documentation-update.md](docs/notes/2026-11-07-architecture-documentation-update.md) | Antigravity |
| 2026-11-07 | Agent Notes & Collaboration Framework Setup | [docs/notes/2026-11-07-agent-framework-setup.md](docs/notes/2026-11-07-agent-framework-setup.md) | Antigravity |

---

## Repository Documentation Index

* **[README.md](README.md)**: Public facing project overview and architecture summary.
* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: System design, data flow, tech stack, and conventions.
* **[docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md)**: Local backend setup, Cloud SQL access, and smoke tests.
* **[docs/notes/](docs/notes/)**: Session-by-session work logs and handoff notes.
* **[docs/decisions/](docs/decisions/)**: Architecture Decision Records (ADRs).
