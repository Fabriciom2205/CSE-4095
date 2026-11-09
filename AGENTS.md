# Agent Operating Guidelines & Workspace Index

Welcome! If you are an AI coding assistant (or human developer) working on this repository, **read this file before beginning work.**

This repository is shared across multiple contributors and agentic workflows. To ensure seamless collaboration and uninterrupted context between sessions, follow the conventions outlined below.

---

## Project Overview

**The Monroe Fund**: A polyglot, performance-tiered, cloud-native agentic trading platform:
* **Frontend:** TypeScript + React (structural type safety, concurrent UI for market visuals & AI reasoning streams).
* **Intelligence Tier ("Brain"):** Python with Gemini SDK / ADK, Model Context Protocol (MCP) servers, and financial API integrations (SEC.gov, SEC EDGAR, Finnhub, Alpaca).
* **Compute & Execution Tier ("Muscle"):** Rust for quantitative backtesting, numerical math, live execution, WebSocket feeds, and deterministic risk checks.
* **Hybrid Interop:** In-process PyO3 + Maturin bindings for on-demand math/backtests; out-of-process Rust daemon over gRPC for live streaming and execution.
* **System of Record:** PostgreSQL (Cloud SQL) for ACID transactional state, ledgers, audit logs, and vector embeddings; Cloud Storage for raw Parquet market data.
* **Cloud Fabric:** Google Cloud Platform (Cloud Run, Cloud Run Jobs, Cloud SQL, Cloud Storage, Secret Manager).
* **Architecture Reference:** Detailed in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
* **Architectural Decisions:** Documented in [docs/decisions/0001-polyglot-trading-platform-architecture.md](docs/decisions/0001-polyglot-trading-platform-architecture.md).

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

* [x] Finalize project scope and high-level architecture in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/decisions/0001-polyglot-trading-platform-architecture.md](docs/decisions/0001-polyglot-trading-platform-architecture.md)
* [x] Implement SEC EDGAR search and in-memory vector RAG agent in [python-brain/](python-brain/)
* [x] Configure environment variables (.env, .env.example) and update project branding to The Monroe Fund
* [x] Implement Model Context Protocol (MCP) server for SEC EDGAR tools in [python-brain/mcp_server.py](python-brain/mcp_server.py)
* [x] Complete codebase audit and refactoring (deduplicate RAG, fix search schema, connection pooling, bounded cache)
* [x] Add python-brain environment & health check script in [python-brain/init.py](python-brain/init.py)
* [x] Add end-to-end MCP server tests (tools, resource, prompt, stdio + streamable-http) in [python-brain/test_mcp_server.py](python-brain/test_mcp_server.py)
* [ ] Fix MCP issues found in testing: generic tool error messages, ignored `start_date` in full-text search, oversized `sec_fetch_filing_text` output (see [docs/notes/2026-11-09-mcp-server-testing.md](docs/notes/2026-11-09-mcp-server-testing.md))
* [ ] Make `test_cache_eviction_bounded` and `test_archive_url_construction` call the real `filing_rag` / `sec_client` code
* [ ] Initialize workspace directory structure (frontend, rust-muscle, proto)
* [ ] Set up protobuf/gRPC definitions for agent-to-daemon communication
* [ ] Configure PyO3/maturin skeleton for Python-Rust in-process bindings
* [ ] Define PostgreSQL schema migrations for accounts, ledgers, and audit logs
* [ ] Set up GCP configuration, Dockerfiles, and CI/CD pipelines (Cloud Build)

---

## Worklogs & Session History

Keep a reverse-chronological list of session notes here. Whenever you create a note in `docs/notes/`, add a row below:

| Date | Topic / Session | Note Link | Contributors / Agent |
| :--- | :--- | :--- | :--- |
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
* **[docs/notes/](docs/notes/)**: Session-by-session work logs and handoff notes.
* **[docs/decisions/](docs/decisions/)**: Architecture Decision Records (ADRs).
