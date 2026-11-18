# Worklog: Live SEC Research Test

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed

## Objective

Verify that the Python agent can answer a research question using a live SEC 10-K.

## Changes Implemented

Recorded the live result and updated the agent backlog. To repeat the test, run this from `python-brain/` and enter an SEC-listed ticker.

```python
from agent import create_sec_agent

ticker = input("Company ticker: ").strip().upper()
chat = create_sec_agent()
response = chat.send_message(
    f"Using the latest SEC 10-K for {ticker}, summarize two material risks in plain English. "
    "Cite the filing date and accession number."
)
print(response.text)
```

## Key Decisions & Context

The command exited successfully. Item 1A supported both risks in the response, and the filing date and accession number matched the EDGAR filing index.

## Known Gotchas, Blockers & Environment Issues

The live run made many embedding requests before answering. This test covered the Python agent with one live filing. MCP transports, PostgreSQL ingestion, and the exact embedding dimension were outside this test.

## Next Steps (Handoff Checklist)

* [ ] Verify live MCP transports and assess filing indexing costs across additional companies.
