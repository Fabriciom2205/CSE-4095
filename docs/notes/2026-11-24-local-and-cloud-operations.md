# Worklog: Local startup and private Cloud Run deployment

* **Date:** 2026-11-24
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Verified

## Objective

Run the local API and its Cloud SQL proxy together and deploy an authenticated hosted API.

## Changes Implemented

* Installed and enabled user systemd services using the [local installer](../../ops/install-local-services.sh). The API waits for real connections to the conversation and SEC reader databases. The managed proxy uses port 5434 so an existing terminal connection on 5433 stays open.
* Built and published a container from the [Dockerfile](../../Dockerfile) to `monroe-services` in Artifact Registry. The image contains the application and dependencies. Local credentials and repository metadata are excluded.
* Deployed private revision `monroe-api-00001-fkw` in `us-east1` with its own service account, an attached Cloud SQL instance, and pinned Secret Manager versions. [Deployment and access](../CLOUD_RUN.md)

## Key Decisions & Context

The local checks reported 41 passes and one skip. The supervised API returned 200 for health, portfolio reads, and SEC filings.

Cloud Run rejected anonymous traffic and required the application credential for protected routes. Authenticated health, portfolio, filings, research, and voice transcription requests returned 200. Research used Vertex and Finnhub, stored the temporary conversation in Cloud SQL, and the verification removed its own session.

## Known Gotchas, Blockers & Environment Issues

Cloud Run requires Google identity and application bearer credentials on protected routes. Local startup uses the existing dotenv file and PostgreSQL password file. The original manual proxy remains available for the pre-existing terminal connection.

## Next Steps (Handoff Checklist)

* [ ] Connect the final frontend to the appropriate local or hosted API and configure its authentication path.
* [ ] Automate deployment when release frequency warrants it.
