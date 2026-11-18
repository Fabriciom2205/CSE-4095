# Worklog: SEC Research Improvements

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Completed; live verification pending

## Objective
Fix the SEC MCP backlog and provide one-call company research.

## Changes Implemented
* `python-brain/sec_client.py`: apply custom date ranges and select latest 10-K metadata from SEC submissions.
* `python-brain/filing_rag.py`: restrict section boundaries to line-start headings rather than inline cross-references.
* `python-brain/mcp_server.py`: surface safe tool errors, bound and clean filing output, and add `sec_company_research` with filing metadata and relevant excerpts.
* `python-brain/test_research.py` and existing MCP tests: add offline regression coverage and update tool registration expectations.

## Key Decisions & Context
The composite uses key sections, returns excerpts rather than a synthesized answer, and limits output to 12,000 characters. Filing tools and resources return up to 30,000 cleaned characters. RAG still reads the original filing.

## Known Gotchas, Blockers & Environment Issues
Six offline regression tests and the offline health check pass. Live SEC calls failed because the sandbox cannot resolve www.sec.gov. MCP prompt and tool dispatch tests hung in the local AnyIO worker even for the existing prompt, so transport behavior remains unverified. Section extraction remains heuristic and needs validation on real filings.

## Next Steps (Handoff Checklist)
* [ ] Run live MCP and composite research tests with SEC network access; validate section boundaries across real filings.
