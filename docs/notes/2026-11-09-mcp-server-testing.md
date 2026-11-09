# Worklog: SEC EDGAR MCP Server Testing

* **Date:** 2026-11-09
* **Contributor / Agent:** Fabricio
* **Branch:** test/mcp-server
* **Status:** Completed

---

## Objective
* Test `python-brain/mcp_server.py` end to end: every tool, the filing resource, the analysis prompt, and the stdio / streamable-http / sse transports as a real MCP client would use them.

---

## Changes Implemented
* [`python-brain/test_mcp_server.py`](../../python-brain/test_mcp_server.py): New test suite. Run with `python test_mcp_server.py` (about 10 s; hits SEC EDGAR live).
  * In-process: exact tool / prompt / resource-template registration, all four SEC tools via `call_tool`, missing-argument validation, `sec://filings/...` resource read, `analyze_sec_filing` prompt rendering (and that every tool it names exists).
  * `sec_query_filing_rag` via MCP (2 Gemini embedding requests; skipped without `GEMINI_API_KEY`).
  * Real clients: spawns `mcp_server.py` over **stdio** and over **streamable-http** on a free local port, then runs the handshake, `list_tools`, a live tool call and a failing tool call.
* [`AGENTS.md`](../../AGENTS.md): Registered this note and updated the backlog.

---

## Key Decisions & Context
* **Separate file:** `test_sec_tools.py` keeps its quick `test_mcp_server` smoke check. The new file covers the MCP surface in depth, with the same plain-assert style and `__main__` runner.
* **SSE tested manually, not in the suite:** `--transport sse` handshake and tool calls work, but SSE is the legacy MCP transport; streamable-http is the Cloud Run path.
* **Default host `0.0.0.0` works:** a client on `127.0.0.1` connects fine to the default `--transport streamable-http` bind (checked manually).

---

## Known Gotchas, Blockers & Environment Issues
Everything listed in the objective works. Issues found (not fixed; reproduction in each bullet):
* **Tool errors reach clients without the cause.** A failing call (e.g. `sec_fetch_filing_text` with `filename="missing.htm"`) returns `is_error=True` with only `Error executing tool sec_fetch_filing_text`. The real reason (`404 Client Error: Not Found for url: ...`) appears only in the server's stderr, so a calling agent can't tell a typo from an outage. Fix: catch exceptions in each tool and raise `mcp.server.mcpserver.exceptions.ToolError` with the message.
* **`sec_full_text_search` ignores `start_date`.** `sec_client.tool_full_text_search` sends `startdt` alone; EFTS only applies it with `dateRange=custom` and `enddt`. With `start_date="2026-01-01"`, results ranged 2009-05-20 .. 2026-11-06; adding `dateRange=custom&enddt=2026-11-09` returned 2026-01-14 .. 2026-11-09. Results are also relevance-ordered, so the tool description's "instant detection of newly published filings" doesn't hold.
* **`sec_fetch_filing_text` and the filing resource return the whole document.** Apple's 10-K is 1,559,032 chars of raw iXBRL HTML (roughly 400K tokens), far more than an agent should pull into one turn. Consider returning cleaned text, a section, or a size cap, and steering agents to `sec_query_filing_rag`.
* **Section extraction truncates Risk Factors / MD&A** (888 and 238 chars on Apple's 10-K) at in-text "Part II, Item 7" cross-references, so `sec_query_filing_rag` with `section="risk_factors"` or `"mda"` sees almost nothing. Fabricio has the details and a proposed patch.
* **Test harness gotcha (Windows):** when spawning the HTTP server, don't leave its stdout on an unread `subprocess.PIPE`. Tracebacks fill the pipe and the server stalls mid-request. The suite logs to a temp file instead.

---

## Next Steps (Handoff Checklist)
* [ ] Surface the underlying error message from failing MCP tools (`ToolError`).
* [ ] Send `dateRange=custom` + `enddt` with `start_date` in `sec_client.tool_full_text_search`.
* [ ] Decide on a size limit or cleaned-text mode for `sec_fetch_filing_text` / the filing resource.
