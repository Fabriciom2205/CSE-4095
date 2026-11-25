# Worklog: Single-file local credentials

* **Date:** 2026-11-25
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed locally

## Objective

Make the local laptop setup work from one environment file and avoid repeated token entry.

## Changes Implemented

* Documented PostgreSQL connection URLs with passwords in `.env` as an alternative to `.pgpass`.
* Added opt-in `MONROE_LOCAL_AUTO_CONNECT=1` for the loopback Vite development server. The proxy reads the token from the repo-root environment and passes it to FastAPI.
* Verified a protected API read through Vite, rejection of cross-origin requests and a POST without a same-origin header, and absence of the API token in served browser modules. The frontend build passed.

## Known Gotchas, Blockers & Environment Issues

Cloud SQL still requires Google Application Default Credentials and the Auth Proxy. The frontend must be opened at the printed `127.0.0.1` URL for automatic connection.

## Next Steps (Handoff Checklist)

* [ ] Copy the local settings onto the presentation laptop and verify its Cloud SQL connection.
