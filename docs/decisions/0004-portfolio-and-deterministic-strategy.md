# ADR 0004: Portfolio data and deterministic strategy evaluation

* **Date:** 2026-11-20
* **Status:** Accepted
* **Authors / Agents:** Codex

## 1. Context & Problem Statement

The backend needs broker positions for portfolio visibility, deterministic risk calculations, and a reproducible way to replay a strategy. The research agent currently calls Gemini through the Python SDK. Its orchestration architecture can be evaluated independently of these capabilities.

## 2. Decision

Keep brokerage reads, risk calculations, and strategy replay in Python modules with explicit inputs. Map normalized Alpaca data to an isolated PostgreSQL portfolio schema when persistence is added. The portfolio client reads accounts, positions, and orders. Its paper order transport is reserved for the trusted execution runner described below. Expose portfolio state to the research agent only under the Phase 4 boundary below.

Represent strategy parameters as data. Evaluate daily signals with observations available at the close, then simulate fills at the next market open. Separate the Massive input fetch from replay so the same input snapshot and strategy produce the same result.

### Phase 4 amendment (2026-11-23)

The agent may read portfolio state and emit proposals. It may never place, size, or approve an order. The portfolio tool surface is limited to a read-only snapshot and proposal validation. Proposal output contains target weights, rationale, evidence, and confidence.

Validation can use deterministic sizing and risk functions internally to evaluate a hypothetical proposal. It returns validation findings. It does not persist orders, expose order quantities to the agent, approve execution, or call a broker write endpoint.

Phase 4 implementation is gated on verifying field mappings against a populated Alpaca paper account. Sector concentration is outside Phase 4 until portfolio symbols can be classified reliably. A configured sector cap must produce an explicit validation error while sector data is unavailable.

### Sector classification and equity retention amendment

Sector limits use the issuer's EDGAR SIC classification grouped by official industry division. Enforce the cap in deterministic proposal and paper execution checks. Block checks when a required position cannot be classified. The execution audit retains the classified projected positions.

Keep detailed equity observations for 90 days and one older high-water mark per account. A separately authorized database maintainer may compact that history. The policy keeps the account peak available to current drawdown checks and leaves decision and fill history outside equity compaction.

### Paper execution amendment

Proposal mode remains the default. In execution mode a trusted local caller can authorize one paper order for a selected symbol by opting in outside the conversation. The agent produces the same target-weight proposal in either mode. It has no tool for submitting an order or changing its authorization, symbol, or risk limits. In the opted-in run, the deterministic backend may turn the target into a buy or sell and submit a paper limit order after fresh account, holdings, quote, and risk checks.

The opt-in expires when the command exits. An order already accepted by Alpaca remains subject to the broker's order lifecycle. This amendment permits the paper runner only and leaves the rest of the Phase 4 boundary in effect.

### Phase 6 execution audit amendment

A paper run requires a stable operator decision key, a shared PostgreSQL ledger, and risk limits and peak equity from that ledger. A deterministic client order ID and intent commit together before submission. Only reconciliation can settle an intent. Daily caps count reserved orders even when the outcome is uncertain. The broker remains authoritative for order state and fills. The API has no execution route.

## 3. Alternatives Considered

* Alpaca's SDK provides account and trading models. The existing HTTP dependency is sufficient for the three read endpoints and keeps the callable surface small.
* Model-driven strategy or risk decisions would make replay and boundary checks dependent on a model. Pure functions give explicit arithmetic and reproducible outputs.
* Switching the research agent to ADK during this work would couple unrelated decisions. A later comparison can reuse these Python modules under either orchestration framework.

## 4. Consequences & Trade-offs

The risk and replay code can be tested without cloud services. The broker client still requires Alpaca credentials, and fresh bar snapshots require Massive entitlements. Portfolio storage is separate from SEC filing storage and requires its own access grants when deployed. Daily bar simulations only model execution and corporate actions supported by their explicit assumptions.
