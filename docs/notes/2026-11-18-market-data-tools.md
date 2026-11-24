# Worklog: Massive and Finnhub market data tools

* **Date:** 2026-11-18
* **Contributor / Agent:** Fabricio
* **Branch:** fabricio/market-data-apis
* **Status:** Completed; verified against live Massive and Finnhub APIs

---

## Objective

Give the research agent and MCP clients market data from Massive and Finnhub, following the [kickoff plan](2026-11-18-market-data-api-kickoff.md).

---

## Changes Implemented

* [python-brain/market_data.py](../../python-brain/market_data.py): New client for both providers. It covers Massive daily bars, previous close, and ticker details, plus Finnhub quotes, company news, basic financial metrics, and the earnings calendar.
* [python-brain/mcp_server.py](../../python-brain/mcp_server.py): Registered seven read-only `massive_*` and `finnhub_*` tools. Results are labeled as untrusted with their provider as the source. `untrusted_data` now accepts a source name that defaults to SEC EDGAR.
* [python-brain/agent.py](../../python-brain/agent.py): Added the market data tools to the Gemini agent. Its instructions now cover missing keys, plan limits, and how to cite the provider and as-of date.
* [python-brain/init.py](../../python-brain/init.py): Reports each market data key and runs one live call per provider when its key is set.
* [python-brain/test_market_data.py](../../python-brain/tests/test_market_data.py): Offline tests covering header-only keys, input validation, errors, normalization, untrusted labeling, and agent wiring. The tool lists in [test_research.py](../../python-brain/tests/test_research.py) and [test_mcp_server.py](../../python-brain/tests/live/mcp_smoke.py) now include the new tools.
* Documented the optional keys in [.env.example](../../.env.example) and [LOCAL_SETUP.md](../LOCAL_SETUP.md), and updated the data sources in the [README](../../README.md) and [architecture](../ARCHITECTURE.md).

---

## Key Decisions & Context

* Both providers share one module because they use the same request, validation, and error handling. Each tool is a thin wrapper, so adding endpoints stays small.
* Keys are read per request from `MASSIVE_API_KEY` and `FINNHUB_API_KEY` and sent only in headers: `Authorization: Bearer` for Massive and `X-Finnhub-Token` for Finnhub. Redirects are refused so the key cannot be forwarded to another host. Requests may only go to `api.massive.com` and `finnhub.io`.
* A missing key disables only that provider's tools. Values starting with `your_` count as missing.
* Output is bounded. Bars and the earnings calendar are limited to 366 days per request. News covers at most 31 days and returns 20 articles with summaries cut to 500 characters.
* Rate limits are not pre-throttled. A 429 is retried twice, after 1 and 2 seconds, and then reported with a plan-limit message.
* Environment variables keep the deployment path unchanged. Cloud Run can inject versioned Secret Manager secrets into the same variables, matching the [database credential plan](../POSTGRESQL.md#runtime-credentials-in-secret-manager).

---

## Known Gotchas, Blockers & Environment Issues

* On 2026-11-18, `init.py` passed 26 checks with both keys set. Each of the seven tools was then called once for AAPL against the live APIs. Every tool returned normalized data, for example a 2026-11-17 close of 351.91 from both Massive and Finnhub. An unknown symbol raised the expected "no quote" error. The plan tiers behind the keys are unconfirmed.
* Massive reports split-adjusted daily volume as a fractional number.
* Daily bar dates come from Massive's millisecond timestamp converted to a UTC date. This is correct for US equities, whose bars start at Eastern midnight.
* Finnhub returns HTTP 200 with zero fields for unknown symbols; the client treats `t == 0` as no quote.
* The agent memoizes tool results per chat session, so a long session reuses its first quote.

---

## Next Steps (Handoff Checklist)

* [x] Add `MASSIVE_API_KEY` and `FINNHUB_API_KEY` to `.env`, run `python python-brain/init.py`, and call each tool once against live data.
* [x] Verify a live agent answer with SEC and Finnhub citations. [Verification](2026-11-24-backend-deliverables.md)
* [ ] Confirm the endpoint scope and plan tiers with Jhoan.
* [ ] Store both keys in Secret Manager alongside the database DSNs when the backend is deployed.
