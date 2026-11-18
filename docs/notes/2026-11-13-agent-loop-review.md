# Worklog: Agent Loop Review

* **Date:** 2026-11-13
* **Contributor / Agent:** Codex
* **Branch:** test/mcp-server
* **Status:** Review completed; fixes pending

## Objective
Investigate why agent research exhausts automatic function calls without answering.

## Findings
* The SDK returns the final unexecuted function call when its automatic call budget is exhausted, and the agent has no recovery path.
* Targeted section extraction silently falls back to the entire document when no matching span is found. The newer end-heading pattern also prevents `SIGNATURES` and end-of-file from terminating financial sections.
* Composite research searches all key sections, so its top results can be unrelated to supply-chain risk; the observed transcript shows off-topic excerpts and repeated searches.
* The working-tree changes since HEAD include a model, API, toolset, prompt, and section extraction change. The precise reason for the model's repeated searches is not established by the partial trace.

## Validation
Inspected the installed Google SDK's `Chat.send_message` and reproduced the financial section fallback using synthetic text. No live requests were made.

## Next Steps (Handoff Checklist)
* [ ] Design bounded function-call exhaustion recovery that preserves valid tool-call history.
* [ ] Test section extraction and risk retrieval using real saved SEC filings.
