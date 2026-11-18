# Worklog: Market data API kickoff (Massive and Finnhub)

* **Date:** 2026-11-18
* **Contributor / Agent:** Fabricio
* **Branch:** fabricio/market-data-apis
* **Status:** Completed; implementation continues in [market data tools](2026-11-18-market-data-tools.md)

---

## Objective

Orient a new Google Cloud project member and scope the Massive and Finnhub API integrations assigned by Jhoan. Jhoan is finishing the database and Secret Manager setup.

---

## Changes Implemented

* No code changes. This note and the [AGENTS.md](../../AGENTS.md#active-tasks--backlog) backlog entry record the assignment.

---

## Key Decisions & Context

* Massive (the company formerly called Polygon.io) and Finnhub are external HTTP APIs authenticated with API keys, not Google Cloud services. Client work does not depend on the database or Secret Manager setup.
* Proposed shape, matching [sec_client.py](../../python-brain/sec_client.py): one client module per provider with a host allowlist, rate limiting, timeouts, and the key read from `MASSIVE_API_KEY` / `FINNHUB_API_KEY`. Send keys in request headers rather than URLs so they stay out of logs.
* Expose the data as MCP tools in [mcp_server.py](../../python-brain/mcp_server.py) and wrap results with `untrusted_data`. News headlines and summaries are third-party text and a prompt-injection surface (see [agent security](2026-11-17-agent-security.md)).
* Reading keys from environment variables keeps the code unchanged when Secret Manager later injects them into a Cloud Run service.

---

## Known Gotchas, Blockers & Environment Issues

* The Google Cloud CLI (594.0.0) is installed, both `gcloud auth login` and ADC succeeded, and the gcloud project, ADC quota project, and `GOOGLE_CLOUD_PROJECT` in `.env` point at the team project. Vertex AI and Cloud SQL Admin APIs are enabled; Secret Manager is not yet.
* `python python-brain/init.py` on Python 3.14.3 passed 21 checks, including live SEC EDGAR, Gemini embeddings, and Gemini chat. `SEC_USER_AGENT` still holds the template placeholder (warning), and the PostgreSQL check was skipped because no Cloud SQL DSN is configured.
* Windows terminals opened before the CLI install do not see `gcloud` until they are restarted or their PATH is reloaded.
* Free plans are rate limited. Check the plan tier Jhoan provisioned before relying on bulk requests.
* Which endpoints Jhoan wants from each provider is unconfirmed.

---

## Next Steps (Handoff Checklist)

* [ ] Confirm with Jhoan which data to pull from each provider and which plan tiers the keys use.
* [x] Implement Massive and Finnhub clients, MCP tools, offline tests, and `init.py` health checks (see [market data tools](2026-11-18-market-data-tools.md)).
* [x] Install the Google Cloud CLI and sign in with `gcloud auth login`.
* [x] Complete ADC login and set the gcloud project and `GOOGLE_CLOUD_PROJECT`.
* [x] Create the virtual environment and run `python python-brain/init.py`.
* [ ] Set `SEC_USER_AGENT` in `.env` to the organization name and a real contact email.
* [ ] After the database setup, start the Cloud SQL Auth Proxy, configure the reader DSN, and rerun `init.py` per [LOCAL_SETUP.md](../LOCAL_SETUP.md).
* [ ] Once Secret Manager is set up, store `MASSIVE_API_KEY` and `FINNHUB_API_KEY` as secrets alongside the database DSNs.
