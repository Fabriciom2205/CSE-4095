# Worklog: Local demo setup

* **Date:** 2026-11-25
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Completed

## Objective

Return to the local Vite and FastAPI setup for the class presentation.

## Changes Implemented

Reverted the uncommitted IAP verifier, hosted frontend packaging, automatic Google sign-in flow, and associated dependency and setup changes. The application files match the pushed local setup in `3518b49`.

## Key Decisions & Context

The user disabled IAP in Google Cloud and chose to run the demo on a new laptop. The local backend uses the repository-root `.env` and the Vite frontend sends the Monroe bearer token through its local API proxy.

## Known Gotchas, Blockers & Environment Issues

A laptop that uses the existing Cloud SQL database also needs fresh Google Application Default Credentials, Cloud SQL Auth Proxy, and any separate PostgreSQL password file referenced by the local connection settings. Local hostname and path settings in the copied environment must match the new machine.

## Next Steps (Handoff Checklist)

* [ ] Follow the [local setup](../LOCAL_SETUP.md) and [frontend startup](../../frontend/README.md) on the presentation laptop.
