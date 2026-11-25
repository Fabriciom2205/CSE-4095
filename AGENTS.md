# Agent Operating Guidelines & Workspace Index

Welcome! If you are an AI coding assistant (or human developer) working on this repository, **read this file before beginning work.**

This repository is shared across multiple contributors and agentic workflows. To ensure seamless collaboration and uninterrupted context between sessions, follow the conventions outlined below.

---

## Project Overview

**The Monroe Fund** is a Python-first AI-assisted financial research project. Near-term work focuses on agentic search, MCP tools, SEC filings, and aggregation of financial data. The backend includes deterministic risk and a daily-bar backtest; a React 19 + Astryx frontend supports investing, paper-only order submission, SEC filings, strategy replay, and research chat. Persistent storage and Google Cloud infrastructure are in use. Rust compute and live execution remain deferred.
* **Architecture Reference:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
* **Architectural Decisions:** [ADR 0001](docs/decisions/0001-polyglot-trading-platform-architecture.md), revised by [ADR 0002](docs/decisions/0002-python-first-research-scope.md). [ADR 0003](docs/decisions/0003-postgresql-sec-research.md) records the SEC PostgreSQL design. [ADR 0004](docs/decisions/0004-portfolio-and-deterministic-strategy.md) records the portfolio and strategy boundaries. [ADR 0005](docs/decisions/0005-phase-5-api-and-agent-runtime.md) covers the API and agent runtime; [ADR 0004](docs/decisions/0004-portfolio-and-deterministic-strategy.md) also records the authenticated paper-order boundary.
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

* [x] Document the active Python research workflow and defer Rust components in the [README architecture overview](README.md#architecture-overview), [detailed architecture](docs/ARCHITECTURE.md#1-near-term-scope), and [Python-first scope decision](docs/decisions/0002-python-first-research-scope.md)
* [x] Implement SEC EDGAR search and in-memory vector RAG agent in [python-brain/](python-brain/)
* [x] Configure environment variables (.env, .env.example) and update project branding to The Monroe Fund
* [x] Implement Model Context Protocol (MCP) server for SEC EDGAR tools in [python-brain/mcp_server.py](python-brain/mcp_server.py)
* [x] Complete codebase audit and refactoring (deduplicate RAG, fix search schema, connection pooling, bounded cache)
* [x] Add python-brain environment & health check script in [python-brain/init.py](python-brain/init.py)
* [x] Add end-to-end MCP server tests (tools, resource, prompt, stdio + streamable-http) in [python-brain/tests/live/mcp_smoke.py](python-brain/tests/live/mcp_smoke.py)
* [x] Fix MCP error messages, date filtering, oversized filing output, and section extraction; add composite research tool (see [docs/notes/2026-11-13-sec-research-improvements.md](docs/notes/2026-11-13-sec-research-improvements.md))
* [x] Run initial live adversarial research tests and verify SEC MCP transport and composite research (see [backlog follow-through](docs/notes/2026-11-24-backend-deliverables.md))
* [x] Add bearer authentication and HTTPS origin controls for shared operator MCP (see [shared MCP access](docs/LOCAL_SETUP.md#shared-mcp-access))
* [ ] Configure deployment ingress and per-user identity before multi-user MCP use
* [x] Retry live agent research after the client lifetime fix (see [docs/notes/2026-11-13-agent-client-lifetime.md](docs/notes/2026-11-13-agent-client-lifetime.md))
* [x] Retry live SEC research after filtering hidden XBRL and validating filing sections (see [docs/notes/2026-11-13-filing-retrieval-noise.md](docs/notes/2026-11-13-filing-retrieval-noise.md))
* [x] Verify linked section extraction on Apple, Microsoft and NVIDIA and run cold/warm retrieval benchmarks
* [x] Make `test_cache_eviction_bounded` and `test_archive_url_construction` call production code
* [x] Remove the mock frontend to focus on completing the backend (see [handoff](docs/notes/2026-11-20-remove-mock-frontend.md))
* [x] Verify live 1536-dimensional embeddings using a real SEC filing and pgvector (see [docs/notes/2026-11-17-postgresql-filing-retrieval.md](docs/notes/2026-11-17-postgresql-filing-retrieval.md))
* [x] Add read-only Alpaca account, position, and order access and portfolio migration 003 (see [portfolio setup](docs/LOCAL_SETUP.md#portfolio-and-strategy-tools))
* [x] Add deterministic portfolio risk checks and a reproducible daily-bar backtest (see [handoff](docs/notes/2026-11-20-portfolio-risk-strategy.md))
* [x] Verify Alpaca paper read access and a reproducible 12-month Massive replay (see [live verification](docs/notes/2026-11-22-live-provider-verification.md))
* [x] Verify Alpaca position and filled order mappings against a populated paper account (see [Phase 4 verification](docs/notes/2026-11-23-phase-4-proposals.md))
* [x] Implement read-only Phase 4 proposals under the [ADR 0004 amendment](docs/decisions/0004-portfolio-and-deterministic-strategy.md#phase-4-amendment-2026-11-23)
* [x] Add separate proposal and explicitly enabled local paper execution modes (see [worklog](docs/notes/2026-11-23-paper-execution-mode.md))
* [x] Add durable paper order intents, database peak and daily caps, and fill reconciliation (see [Phase 6 handoff](docs/notes/2026-11-23-paper-order-audit.md))
* [ ] Provision the shared execution database and run the paper submission and duplicate-key smoke test during regular market hours
* [x] Add trusted equity history to HTTP proposal drawdown checks through a scoped reader role
* [x] Define equity snapshot retention and enforce sector caps using EDGAR SIC classifications
* [ ] Configure the intended proposal equity reader and schedule the snapshot retention operation
* [x] Serve the Phase 5 FastAPI contract with ADK specialists and durable sessions (see [Phase 5 handoff](docs/notes/2026-11-23-phase-5-api-implementation.md))
* [x] Add authenticated research audio transcription for the future frontend
* [x] Add opt-in structured SEC statement tables and charts to research JSON and streaming responses (see [research visuals](docs/notes/2026-11-24-research-visuals.md))
* [x] Reduce research model calls and parallelize proposal evidence reads (see [agent performance review](docs/notes/2026-11-23-agent-performance.md))
* [x] Group backend tests and opt-in live checks under [python-brain/tests/](python-brain/tests/) (see [test layout handoff](docs/notes/2026-11-23-backend-test-layout.md))
* [ ] Measure generation and embedding cost across representative research and proposal requests before changing the model or adding billing dashboards
* [x] Verify local API startup, bearer auth, and SQLite session lookup with the project virtual environment
* [x] Verify local API conversations persist in the dedicated Cloud SQL session database through the Auth Proxy
* [x] Configure the private Cloud Run API token and connect its dedicated session database through Cloud SQL
* [x] Install local user services for one-command startup of the API and Cloud SQL proxy
* [ ] Deferred: Initialize remaining workspace directories (rust-muscle, proto)
* [ ] Deferred: Set up protobuf/gRPC definitions if a Rust daemon is needed
* [ ] Deferred: Configure PyO3/maturin bindings if measured compute needs justify them
* [x] Add PostgreSQL schema, SEC fact and latest auditor import, and Cloud SQL guide ([setup](docs/POSTGRESQL.md))
* [x] Verify the importer against live EDGAR and load historical auditors and standard explicit-dimensional facts
* [ ] Extend dimensional and historical relationship coverage beyond the first loader
* [x] Implement PostgreSQL-backed agent and MCP filing retrieval following [the retrieval plan](docs/notes/2026-11-17-postgresql-retrieval-plan.md)
* [x] Add a single-command PostgreSQL filing retrieval check for the agent and its shared MCP tool (see [setup](docs/POSTGRESQL.md#enable-persistent-filing-retrieval))
* [x] Apply migration 002 and scoped database grants to Cloud SQL (see [verification](docs/notes/2026-11-17-cloud-sql-filing-retrieval.md))
* [x] Configure local Cloud SQL runtime DSNs and verify both cold indexing and reader-only reuse with `python python-brain/init.py --postgres TICKER` (see [verification](docs/notes/2026-11-17-cloud-sql-filing-retrieval.md) and [smoke commands](docs/notes/2026-11-17-agent-smoke-commands.md))
* [x] Document local backend and Cloud SQL setup, password-file configuration, and 10-Q verification in [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md)
* [ ] Configure Secret Manager references for the database roles when deploying the backend (see [setup](docs/POSTGRESQL.md#runtime-credentials-in-secret-manager))
* [x] Prepare the shared security and PostgreSQL changes for the main branch (see [release handoff](docs/notes/2026-11-17-security-postgresql-release.md))
* [x] Implement Massive and Finnhub market data clients, MCP tools, and agent tools (see [market data tools](docs/notes/2026-11-18-market-data-tools.md))
* [x] Verify the Massive and Finnhub tools against live APIs (see [market data tools](docs/notes/2026-11-18-market-data-tools.md))
* [ ] Deferred: Scope Alpaca market data or brokerage access if requested (see [Alpaca status](docs/notes/2026-11-20-alpaca-status.md))
* [x] Verify Finnhub general news and NVDA company news against the live API (see [news verification](docs/notes/2026-11-22-finnhub-news-check.md))
* [x] Verify an end-to-end research answer with SEC and Finnhub citations
* [ ] Confirm market data endpoint scope and plan tiers with Jhoan
* [x] Add opt-in PostgreSQL reads for consolidated financial facts and statements, with automatic EDGAR fallback and typed relationship reads (see [research routing](docs/notes/2026-11-20-sec-research-routing.md))
* [x] Add an all-forms SEC filing timeline, linked section navigation, and annual risk-factor text diff (see [filing navigation](docs/notes/2026-11-20-sec-filing-navigation.md))
* [x] Add SEC Figure Source research for Form 4 transactions and 13F holdings changes (see [handoff](docs/notes/2026-11-23-figure-sources.md))
* [x] Add indexed cross-filing narrative retrieval with repeated-passage deduplication and explicit coverage gaps
* [ ] Expand statement coverage and imported data across more issuers and filing periods before relying on broad SQL coverage
* [x] Deploy the Python API privately on Cloud Run with a scoped service account and pinned secret references
* [x] Create the React 19 + Astryx frontend with investing, proposal and paper-order modes, broker orders, SEC filings, configurable strategy replays, and streaming Phil research visuals (see [frontend setup](frontend/README.md))
* [x] Build the React 19 investing dashboard, asset detail and paper-order screens, SEC filings, strategy replay, and floating Phil voice chat
* [x] Add Monroe logo, searchable stocks/ETFs, and selectable hoverable asset price charts (see [handoff](docs/notes/2026-11-24-asset-search-chart.md))
* [x] Fix Phil message contrast and reserve model calls for research replies, and split the frontend JavaScript bundle (see [handoff](docs/notes/2026-11-24-phil-research-and-bundle.md))
* [x] Distinguish proposal evidence retrieval failures from model and validation failures (see [handoff](docs/notes/2026-11-25-proposal-error-diagnostics.md))
* [x] Fall back to direct SEC annual filing excerpts when proposal filing search fails (see [handoff](docs/notes/2026-11-25-proposal-filing-fallback.md))
* [x] Add momentum, quality/value, and news sentiment research replays with a benchmark and period-specific asset returns (see [handoff](docs/notes/2026-11-25-ranked-strategy-replays.md))
* [x] Add authenticated portfolio history, order history, direct paper-order, and explicitly confirmed agent paper-run API routes
* [x] Surface proposals, strategy tuning and browser drafts, saved replay, streaming Phil markdown, SEC statement tables and charts, and read-only broker orders
* [x] Verify the new local market quote and price history routes through the Vite proxy
* [x] Return to local setup for the class demo and remove the IAP-only implementation from the workspace (see [laptop handoff](docs/notes/2026-11-25-local-demo-setup.md))
* [x] Document password-bearing database URLs and support token-free local frontend startup through the Vite proxy (see [credential handoff](docs/notes/2026-11-25-local-credential-shortcuts.md))
* [ ] Automate test-gated image publication and Cloud Run revisions when CI/CD is needed

---

## Worklogs & Session History

Keep a reverse-chronological list of session notes here. Whenever you create a note in `docs/notes/`, add a row below:

| Date | Topic / Session | Note Link | Contributors / Agent |
| :--- | :--- | :--- | :--- |
| 2026-11-25 | Single-file local credentials | [docs/notes/2026-11-25-local-credential-shortcuts.md](docs/notes/2026-11-25-local-credential-shortcuts.md) | Codex |
| 2026-11-25 | Local demo setup and IAP cleanup | [docs/notes/2026-11-25-local-demo-setup.md](docs/notes/2026-11-25-local-demo-setup.md) | Codex |
| 2026-11-25 | Cloud Run IAP demo revision deployed | [docs/notes/2026-11-25-cloud-run-iap-deploy.md](docs/notes/2026-11-25-cloud-run-iap-deploy.md) | Codex |
| 2026-11-25 | Cloud Run frontend and IAP authentication | [docs/notes/2026-11-25-cloud-run-iap-ui.md](docs/notes/2026-11-25-cloud-run-iap-ui.md) | Codex |
| 2026-11-25 | Frontend release and class demo handoff | [docs/notes/2026-11-25-frontend-release-handoff.md](docs/notes/2026-11-25-frontend-release-handoff.md) | Codex |
| 2026-11-25 | Ranked strategy replays and asset period returns | [docs/notes/2026-11-25-ranked-strategy-replays.md](docs/notes/2026-11-25-ranked-strategy-replays.md) | Codex |
| 2026-11-25 | Direct filing fallback for proposals | [docs/notes/2026-11-25-proposal-filing-fallback.md](docs/notes/2026-11-25-proposal-filing-fallback.md) | Codex |
| 2026-11-25 | Proposal error diagnostics | [docs/notes/2026-11-25-proposal-error-diagnostics.md](docs/notes/2026-11-25-proposal-error-diagnostics.md) | Codex |
| 2026-11-24 | Phil chat contrast, research budget, and JavaScript bundles | [docs/notes/2026-11-24-phil-research-and-bundle.md](docs/notes/2026-11-24-phil-research-and-bundle.md) | Codex |
| 2026-11-24 | Monroe logo, ticker search, and hoverable asset charts | [docs/notes/2026-11-24-asset-search-chart.md](docs/notes/2026-11-24-asset-search-chart.md) | Codex |
| 2026-11-24 | Full backend feature UI and formatted Phil | [docs/notes/2026-11-24-backend-feature-frontend.md](docs/notes/2026-11-24-backend-feature-frontend.md) | Codex |
| 2026-11-24 | Investing dashboard and paper orders | [docs/notes/2026-11-24-investing-dashboard.md](docs/notes/2026-11-24-investing-dashboard.md) | Codex |
| 2026-11-24 | Local market data service restart | [docs/notes/2026-11-24-local-market-data-smoke.md](docs/notes/2026-11-24-local-market-data-smoke.md) | Codex |
| 2026-11-24 | Trading desk, Phil chat, and voice input | [docs/notes/2026-11-24-trading-desk-phil.md](docs/notes/2026-11-24-trading-desk-phil.md) | Codex |
| 2026-11-24 | React 19 + Astryx frontend | [docs/notes/2026-11-24-astryx-frontend.md](docs/notes/2026-11-24-astryx-frontend.md) | Codex |
| 2026-11-24 | Local startup and private Cloud Run deployment | [docs/notes/2026-11-24-local-and-cloud-operations.md](docs/notes/2026-11-24-local-and-cloud-operations.md) | Codex |
| 2026-11-24 | Cloud SQL conversation persistence | [docs/notes/2026-11-24-cloud-sql-conversations.md](docs/notes/2026-11-24-cloud-sql-conversations.md) | Codex |
| 2026-11-24 | Voice research and portfolio and MCP controls | [docs/notes/2026-11-24-voice-and-portfolio-controls.md](docs/notes/2026-11-24-voice-and-portfolio-controls.md) | Codex |
| 2026-11-24 | Opt-in SEC research visuals | [docs/notes/2026-11-24-research-visuals.md](docs/notes/2026-11-24-research-visuals.md) | Codex |
| 2026-11-24 | Backend deliverables and live verification | [docs/notes/2026-11-24-backend-deliverables.md](docs/notes/2026-11-24-backend-deliverables.md) | Codex |
| 2026-11-23 | Backend test layout | [docs/notes/2026-11-23-backend-test-layout.md](docs/notes/2026-11-23-backend-test-layout.md) | Codex |
| 2026-11-23 | Agent latency and model usage review | [docs/notes/2026-11-23-agent-performance.md](docs/notes/2026-11-23-agent-performance.md) | Codex |
| 2026-11-23 | SEC Figure Source research | [docs/notes/2026-11-23-figure-sources.md](docs/notes/2026-11-23-figure-sources.md) | Codex |
| 2026-11-23 | Main backend release handoff | [docs/notes/2026-11-23-main-backend-handoff.md](docs/notes/2026-11-23-main-backend-handoff.md) | Codex |
| 2026-11-23 | Phase 6 paper order audit and reconciliation | [docs/notes/2026-11-23-paper-order-audit.md](docs/notes/2026-11-23-paper-order-audit.md) | Codex |
| 2026-11-23 | Local API startup and session storage | [docs/notes/2026-11-23-local-api-startup.md](docs/notes/2026-11-23-local-api-startup.md) | Codex |
| 2026-11-23 | Phase 5 FastAPI and ADK implementation | [docs/notes/2026-11-23-phase-5-api-implementation.md](docs/notes/2026-11-23-phase-5-api-implementation.md) | Codex |
| 2026-11-23 | ADK specialists and durable conversations | [docs/notes/2026-11-23-adk-specialists.md](docs/notes/2026-11-23-adk-specialists.md) | Codex |
| 2026-11-23 | Phase 5 runtime and API decision | [docs/notes/2026-11-23-phase-5-runtime-decision.md](docs/notes/2026-11-23-phase-5-runtime-decision.md) | Codex |
| 2026-11-23 | Opt-in paper execution mode | [docs/notes/2026-11-23-paper-execution-mode.md](docs/notes/2026-11-23-paper-execution-mode.md) | Codex |
| 2026-11-23 | Phase 4 proposals and live position verification | [docs/notes/2026-11-23-phase-4-proposals.md](docs/notes/2026-11-23-phase-4-proposals.md) | Codex |
| 2026-11-23 | Phase 4 proposal preflight | [docs/notes/2026-11-23-phase-4-preflight.md](docs/notes/2026-11-23-phase-4-preflight.md) | Codex |
| 2026-11-22 | Finnhub news verification | [docs/notes/2026-11-22-finnhub-news-check.md](docs/notes/2026-11-22-finnhub-news-check.md) | Codex |
| 2026-11-22 | Live Alpaca and Massive verification | [docs/notes/2026-11-22-live-provider-verification.md](docs/notes/2026-11-22-live-provider-verification.md) | Codex |
| 2026-11-20 | Portfolio, risk, and strategy replay | [docs/notes/2026-11-20-portfolio-risk-strategy.md](docs/notes/2026-11-20-portfolio-risk-strategy.md) | Codex |
| 2026-11-20 | Remove mock frontend | [docs/notes/2026-11-20-remove-mock-frontend.md](docs/notes/2026-11-20-remove-mock-frontend.md) | Codex |
| 2026-11-20 | Alpaca integration status | [docs/notes/2026-11-20-alpaca-status.md](docs/notes/2026-11-20-alpaca-status.md) | Codex |
| 2026-11-20 | Filing timeline and linked sections | [docs/notes/2026-11-20-sec-filing-navigation.md](docs/notes/2026-11-20-sec-filing-navigation.md) | Codex |
| 2026-11-20 | Typed SEC research and filing discovery | [docs/notes/2026-11-20-sec-research-routing.md](docs/notes/2026-11-20-sec-research-routing.md) | Codex |
| 2026-11-18 | Massive and Finnhub market data tools | [docs/notes/2026-11-18-market-data-tools.md](docs/notes/2026-11-18-market-data-tools.md) | Fabricio |
| 2026-11-18 | Market data API kickoff (Massive and Finnhub) | [docs/notes/2026-11-18-market-data-api-kickoff.md](docs/notes/2026-11-18-market-data-api-kickoff.md) | Fabricio |
| 2026-11-17 | README architecture diagram | [docs/notes/2026-11-17-readme-architecture-diagram.md](docs/notes/2026-11-17-readme-architecture-diagram.md) | Codex |
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
