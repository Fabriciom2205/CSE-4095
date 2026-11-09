# Worklog: Python Brain Health Check (init.py)

* **Date:** 2026-11-09
* **Contributor / Agent:** Fabricio
* **Branch:** main
* **Status:** Completed

---

## Objective
* Add a single script that verifies every `python-brain` file runs as intended: environment, dependencies, imports, agent/MCP wiring, and live SEC EDGAR + Gemini connectivity.

---

## Changes Implemented
* [`python-brain/init.py`](../../python-brain/init.py): New health check script. Run `python init.py` (or `python init.py --offline` to skip network calls) from `python-brain/`, or `python python-brain/init.py` from the repo root. Exits `1` if any check fails.
  * **Environment:** Python >= 3.11, every `requirements.txt` package installed at its minimum version, `.env` discovered, `GEMINI_API_KEY` / `SEC_USER_AGENT` set and not left at their `.env.example` placeholders. Finnhub / Alpaca / `DATABASE_URL` are reported as `SKIP` since `python-brain` does not read them yet.
  * **Modules:** imports `sec_client`, `filing_rag`, `agent`, `mcp_server`; confirms MCP tools, prompts and resource templates register; constructs the SEC agent.
  * **Live connectivity:** `www.sec.gov` (CIK lookup), `efts.sec.gov` (full-text search fields populated), `data.sec.gov` (XBRL facts), Gemini embeddings (reports when `filing_rag` would silently fall back to `text-embedding-004`), and one Gemini agent chat turn (validates the key, the chat model, and every tool declaration).
* [`AGENTS.md`](../../AGENTS.md): Registered this note and updated the backlog.

---

## Key Decisions & Context
* **Named `init.py`, not `__init__.py`:** `__init__.py` is Python's package marker and runs on every import, so it can't host a standalone check. `python-brain` stays a flat directory of scripts.
* **Live checks on by default:** "Running as intended" depends on SEC and Gemini actually answering. SEC calls are free and rate-limited by `sec_client`; the Gemini checks cost one embedding and one short chat turn. `--offline` skips them all.
* **Minimum Python 3.11:** `google-genai` 3.x requires it (`numpy` 2.5 needs 3.12, but older `numpy` 2.x releases still satisfy `requirements.txt` on 3.11).
* **No secrets in output:** Key values are never printed; the Gemini key is redacted from any API error text.
* **Venv location:** Used `python-brain/.venv` (already covered by `.gitignore`).

---

## Known Gotchas, Blockers & Environment Issues
* **Verified end to end with a real key:** `gemini-embedding-2` (3072 dimensions) and `gemini-2.5-flash` both respond, and Gemini accepts all five agent tool declarations. With a fake key both checks fail with `API key not valid`.
* **`SEC_USER_AGENT` placeholder is a `WARN`, not a `FAIL`:** SEC still answers requests that use the template contact, but its fair-access policy asks for a real email.
* **Existing tests (`python test_sec_tools.py`) pass** on a fresh Python 3.14 venv, but two of them don't exercise production code:
  * `test_cache_eviction_bounded` re-implements the FIFO eviction inside the test instead of calling `filing_rag.index_filing`, so a regression in `index_filing` would not be caught.
  * `test_archive_url_construction` rebuilds the archive URL inline instead of calling `sec_client.tool_fetch_filing_text`.

---

## Next Steps (Handoff Checklist)
* [ ] Point `test_cache_eviction_bounded` and `test_archive_url_construction` at the real `filing_rag` / `sec_client` code.
* [ ] Confirm the scope of the next MCP server task: the SEC EDGAR MCP server already exists in `python-brain/mcp_server.py`.
