# ADR 0002: Prioritize Python Financial Research

* **Date:** 2026-11-16
* **Status:** Accepted
* **Authors / Agents:** Project contributors, Codex
* **Supersedes:** ADR 0001 in part (near-term scope and priorities)

## 1. Context & Problem Statement

The project needs to focus limited time on agentic search and aggregation of financial data. The existing architecture places Rust execution and backtesting alongside Python intelligence as core commitments, while current implementation is concentrated in Python research and MCP.

## 2. Decision

Prioritize Python agents, MCP tools, financial data ingestion and aggregation, retrieval quality, and grounded AI-assisted research. Connect the research interface and add storage or deployment infrastructure as needed to support this work. Rust, PyO3, gRPC, backtesting, and execution remain possible later work rather than prerequisites for Python research. Revisit them when concrete requirements and measurements justify the investment.

Live order execution is outside the immediate scope. A future execution design must define and validate independent risk controls, authorization, and auditability before placing orders.

## 3. Alternatives Considered

* **Continue the original parallel Python/Rust build:** Deferred because it divides effort away from the immediate research goal.
* **Rule out Rust permanently:** Rejected because later compute or execution requirements may justify it.

## 4. Consequences & Trade-offs

* Focused development can improve the research workflow and its data quality sooner, with fewer toolchains to maintain now.
* High-performance backtesting and live execution are deferred. Python performance and retrieval costs still need measurement; future requirements may require revisiting the architecture.
