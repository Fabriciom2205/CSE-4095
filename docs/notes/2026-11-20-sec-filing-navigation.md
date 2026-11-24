# Worklog: Filing timeline and linked sections

* **Date:** 2026-11-20
* **Contributor / Agent:** Codex
* **Branch:** fabricio/market-data-apis
* **Status:** Implemented

## Objective

Use existing SEC submissions and archived filing documents to follow a filer across forms and compare annual risk-factor disclosures.

## Changes Implemented

* [SEC client](../../python-brain/sec_client.py) shares submission traversal between the existing latest-filing lookup and the bounded filing timeline. The timeline prunes older archive files by the filing date filter and handles links to ownership-form XML.
* [Section navigation](../../python-brain/filing_sections.py) follows the filing's own table-of-contents links for 10-K Items and 10-Q Parts. The annual Item 1A diff compares paragraphs from consecutive fiscal years and cites both filings.
* [MCP tools](../../python-brain/mcp_server.py) and [agent routing](../../python-brain/agent.py) expose the timeline, section excerpts, and annual diff as read-only tools.
* [Regression tests](../../python-brain/test_filing_navigation.py) cover archived submissions, document links, section boundaries, hidden text, and diff citations. Live SEC checks exercised Apple's timeline, a 10-Q, and annual risk-factor comparisons.

## Key Decisions & Context

* The diff runs on extracted text without embeddings. The agent can interpret differences in wording using the quoted evidence.
* The current pgvector index keys include accession and section. Temporal retrieval would need a metadata query across indexes and a way to deduplicate repeated passages. Peer comparison needs aligned financial periods and a wider verified fact catalog.
* Dimensional XBRL loading remains a prerequisite for segment coverage. Footnotes, ratios, red flags, and cost instrumentation have distinct data or measurement needs and were left for separate work.

## Known Gotchas, Blockers & Environment Issues

* Deterministic navigation requires recognizable linked headings. The tools report an unavailable or ambiguous section rather than returning unrelated filing text. Large excerpts and diffs are marked as truncated.

## Next Steps (Handoff Checklist)

* [ ] Check linked filings from more issuers before extending the parser to filings without linked contents.
* [ ] Evaluate cross-filing retrieval against the current pgvector schema and define boilerplate deduplication.
