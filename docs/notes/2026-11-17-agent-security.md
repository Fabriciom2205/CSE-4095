# Worklog: Agent and MCP Security

* **Date:** 2026-11-17
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed

## Objective

Reduce prompt-injection and tool misuse risks for Python research and the SEC MCP server.

## Changes Implemented

* Updated [agent](../../python-brain/agent.py) and [MCP server](../../python-brain/mcp_server.py) instructions to treat external content as untrusted. Structured responses and filing resources label external data; response shapes have changed.
* Annotated research tools read-only, restricted SEC request destinations and redirects, validated filing identifiers and bounded retrieval parameters, and defaulted HTTP/SSE to localhost.
* Documented data flows and deployment requirements in the [README](../../README.md); added offline regression checks.

## Key Decisions & Context

Tool annotations and untrusted-data labels are hints, not security boundaries or a guarantee against prompt injection. RAG sends questions and filing chunks to Google embeddings; model conversations go to Google, and SEC searches send queries to SEC. Read-only does not prevent disclosure through outgoing requests.

## Known Gotchas, Blockers & Environment Issues

HTTP/SSE has no application authentication or per-user authorization. Existing external MCP consumers must update for the structured result envelope. Live SEC, cloud, transport and adversarial model behavior were not verified in this session.

## Next Steps (Handoff Checklist)

* [ ] Run adversarial model evaluations and verify live SEC retrieval and transports.
* [ ] Before remote or multi-user deployment, implement and verify authentication, authorization, TLS, network restrictions, rate limits, and least-privilege service identities.
