# ADR 0005: Phase 5 API and agent runtime

* **Date:** 2026-11-23
* **Status:** Accepted
* **Authors / Agents:** Codex

## 1. Context & Problem Statement

The frontend prototype is gone. Phase 5 needs a typed contract for a future frontend. The existing Gemini SDK agent has chat history within a chat object. The MCP server serves tools, but there is no application HTTP API, frontend session lifecycle, or research response stream.

## 2. Decision

Use ADK behind FastAPI. Keep the HTTP models separate from the agent runtime and keep Gemini as the model provider. A coordinator delegates to narrow specialists and receives bounded evidence summaries. Start with SEC research and market data specialists. Proposal generation is a separate, private workflow using shared source tools for evidence and the existing deterministic risk functions for checks. Public research specialists receive no portfolio or execution tools.

The coordinator can call the shared evidence tools directly for single-company and single-filer lookups. Keep specialists for comparisons across companies or filers. The private proposal workflow gathers evidence with bounded parallel reads and fetches quotes after filing retrieval. Use one model-call budget per run across the coordinator, specialists, and compaction.

Persist session history and accepted proposal context in PostgreSQL with ADK's database session service and a dedicated session database role. The application controls session IDs and ownership. Keep brokerage snapshots and exposure calculations outside the model session. Store bounded SEC and market evidence with the conversation and compact older context. Persisting a conversation or proposal does not persist execution authorization or make a historical quote current.

Keep JSON as the default response. Allow research to create or resume a conversation by session ID. Offer a bounded SSE stream of public progress and answer events when requested. Continue to use FastAPI for authentication and the application contract instead of exposing ADK's development server as the product API.

| Route | Contract |
| --- | --- |
| GET /health | Minimal service readiness without a provider network call |
| GET /filings | Use EFTS for keyword queries and submissions for a ticker timeline. Define combined filters and response limits explicitly. |
| POST /research | Accept ticker, question, and an optional session ID. Return the session ID, answer, and typed citations checked against evidence. Document optional SSE delivery. |
| POST /research/transcribe | Accept a bounded audio recording and return a transcript for review. The client submits the reviewed text to the research route. |
| GET /portfolio | Return account, positions, exposures, and retrieval and freshness metadata. Use read-through Alpaca data with a short bounded cache. |
| POST /proposals | Accept a ticker or universe, constraints, and an optional private session ID. Return schema-valid proposals with deterministic breach findings and freshness status. |
| POST /backtest | Accept strategy and snapshot ID. Replay only a server-known snapshot. Return the snapshot hash and replay result. |

Use a server-configured bearer token for application data and quota-consuming routes. Fail closed when the token is missing and bind locally by default. Serve remotely over TLS. Keep paper execution outside the HTTP surface.

Start with a 15-second portfolio cache. Report the retrieval timestamp and age separately from the provider's market timestamp. A fetched Alpaca position without a mark timestamp has unknown market freshness. A proposal can report results evaluated on those reported marks, but it cannot claim a live-price check. Report dated quotes used in the evaluation and reject or mark stale quotes according to a documented limit. Disable chat-lifetime quote memoization for freshness-sensitive calculations. Defer persisted portfolio snapshots to Phase 6.

The API needs a trusted historical equity peak when drawdown is evaluated. Until a source exists, require an operator-provided peak for that check. The current CLI rejects breached proposals, while the HTTP proposal route should return breaches as data and preserve the CLI behavior.

## 3. Alternatives Considered

* Keep the SDK as the sole runtime. It already supports multi-turn chat and token streaming. We would own specialist delegation, session persistence, context boundaries, and tool event routing.
* Expose the MCP or ADK server directly as the frontend API. Their transport and event models are useful for tool and agent clients. The frontend needs stable domain responses and one application auth boundary.

## 4. Consequences & Trade-offs

ADK adds orchestration and session infrastructure. It also adds model calls when work is delegated. Specialist tool scopes and bounded handoffs must be designed explicitly to reduce context growth. Keep the current SDK entry points available for local CLI and MCP workflows. Measure tool counts, cost, and latency on representative requests before expanding the specialist tool sets.

Phase 5 acceptance requires OpenAPI coverage of all six domain routes, authentication tests, a schema-valid proposal with evidence for a real ticker, and successful conversation recovery across a service restart. Paper execution stays local and requires a new user opt-in per run.
