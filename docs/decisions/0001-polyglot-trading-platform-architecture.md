# ADR 0001: The Monroe Fund Polyglot Cloud-Native Trading Platform Architecture

* **Date:** 2026-11-07
* **Status:** Accepted
* **Authors / Agents:** Antigravity (Assistant), Marlon, Fabricio, Misael
* **Supersedes:** None

---

## 1. Context & Problem Statement

Building The Monroe Fund as an autonomous agentic trading platform requires simultaneously satisfying conflicting system requirements:
1. **Dynamic Intelligence & Flexibility:** Rapid integration with evolving LLM ecosystems (Gemini SDK/ADK), Model Context Protocol (MCP) tool suites, and semi-structured external financial data feeds (SEC EDGAR, Finnhub, Alpaca).
2. **Deterministic Low-Latency & Safety:** High-speed numerical backtesting, unbroken WebSocket streaming, deterministic risk checks, and zero-overhead execution without garbage collection jitter or interpreter lock contention.
3. **Auditable Transactional Integrity:** Absolute consistency across user balances, orders, execution fills, and immutable agent reasoning audit trails.
4. **Interactive Real-Time Interface:** Non-blocking visualization of high-frequency market depth alongside streaming AI thought processes.

A single-language monolith fails to satisfy these requirements: pure Python suffers from GIL bottlenecks and GC pauses in live streaming and backtesting; pure Rust slows down agent prototyping and lacks native LLM SDK ecosystems.

---

## 2. Decision

We adopt a tiered polyglot cloud-native architecture:
* **Frontend:** TypeScript + React for structural type-safety and concurrent non-blocking UI rendering.
* **Brain (Intelligence Tier):** Python for agent orchestration (Gemini SDK/ADK), MCP tool servers, and financial API integrations.
* **Muscle (Execution & Compute Tier):** Rust for numerical math, backtesting, deterministic risk verification, WebSocket streams, and live execution.
* **Python-Rust Interop:** A two-part hybrid model:
  1. *In-process:* PyO3 + Maturin compiled extensions for on-demand math and backtesting workloads.
  2. *Out-of-process:* An autonomous Rust daemon communicating with Python agents over gRPC for live streaming and broker execution.
* **System of Record:** PostgreSQL (Cloud SQL) for ACID-compliant transactional state and vector embeddings (`pgvector`), combined with Google Cloud Storage for raw Parquet market data.
* **Cloud Infrastructure:** Google Cloud Platform (Cloud Run, Cloud Run Jobs, Cloud SQL, Cloud Storage, Secret Manager).

---

## 3. Alternatives Considered

* **Monolithic Python (FastAPI + Asyncio):**
  * *Rejected:* Python's Global Interpreter Lock (GIL) and runtime overhead introduce non-deterministic latency spikes during heavy market data streaming and concurrent backtesting.
* **Monolithic Rust (Tauri / WebAssembly / Pure Rust Backend):**
  * *Rejected:* Slower development velocity for AI agents; LLM frameworks, MCP tooling, and financial ingestion libraries are overwhelmingly prioritized in the Python ecosystem.
* **Single IPC Mechanism (gRPC only):**
  * *Rejected:* Passing massive market tick datasets over network sockets or serialization barriers during large backtests introduces unnecessary overhead compared to in-process PyO3 zero-copy memory bindings.

---

## 4. Consequences & Trade-offs

* **Positive Consequences:**
  * Clean separation of concerns: AI layer stays agile while execution remains fast, safe, and deterministic.
  * Maximum throughput for quantitative computations via compiled native Rust code.
  * Zero-downtime scalability via GCP serverless and containerized deployment models.
  * Strict compile-time risk boundaries preventing hallucinated agent actions from placing unvalidated orders.
* **Negative Consequences / Trade-offs:**
  * Multi-language build toolchains required (Cargo, Maturin, Poetry/Pipenv, Node/npm, Docker).
  * Requires maintaining schema synchronization across Protobuf/gRPC definitions and TypeScript interfaces.
