# Worklog: Voice research and portfolio and MCP controls

* **Date:** 2026-11-24
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Add recorded research questions to the API and implement the open portfolio and shared MCP controls.

## Changes Implemented

* [Voice endpoint](../../python-brain/api.py) accepts bounded audio and returns a transcript. The frontend can present the transcript for review and send it through the existing research route. The application does not store uploaded audio.
* [Sector lookup](../../python-brain/portfolio_sectors.py) uses SEC issuer SIC codes grouped by official industry division. HTTP and CLI proposal and paper risk checks require available classifications whenever the sector cap is set.
* [Equity retention migration](../../db/migrations/005_equity_retention.sql) keeps 90 days of detail and an older peak for each account. The database operator invokes the maintenance function separately.
* [MCP access layer](../../python-brain/mcp_access.py) checks a separate bearer token, Host, Origin, and explicit TLS settings for a non-loopback listener. The tool surface remains scoped to research.

## Key Decisions & Context

The voice endpoint uses the existing Gemini project and accepts common browser recording containers. Operator review keeps transcription separate from submitting a question. SIC sectors describe an issuer's reported business and do not expand a fund's underlying holdings.

All 121 Python tests and both PostgreSQL checks passed. The retention migration was tested on disposable PostgreSQL. A synthesized WebM question transcribed correctly through live Gemini. Live EDGAR returned classifications for Apple, Microsoft, and NVIDIA. A local HTTPS process returned 401 without credentials, 403 for a foreign Origin, and 200 with valid bearer authentication.

## Known Gotchas, Blockers & Environment Issues

The shared MCP credential represents one operator. Deployment needs an exact HTTPS origin and ingress controls. The equity maintenance function needs an authorized maintenance schedule after applying migration 005 to the deployment database.

## Next Steps (Handoff Checklist)

* [ ] Wire a microphone recorder and transcript review into the final frontend.
* [ ] Configure the deployment database maintenance schedule and set the shared MCP credentials and ingress when deploying.
