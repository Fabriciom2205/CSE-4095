# Worklog: Cloud Run frontend and IAP authentication

* **Date:** 2026-11-25
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Superseded by the [local demo setup](2026-11-25-local-demo-setup.md)

## Objective

Package the app for a shared Google sign-in demo while preserving Alpaca paper execution.

## Changes Implemented

* [Dockerfile](../../Dockerfile) builds the same-origin React frontend into the Cloud Run image. FastAPI serves the UI alongside its API routes.
* [IAP verifier](../../python-brain/iap_auth.py) verifies Google signatures and service-specific claims. In IAP mode, protected routes require the signed assertion and POST requests require a header that a cross-origin browser cannot send without preflight permission.
* [Frontend](../../frontend/src/App.tsx) loads the account automatically in IAP mode. The local bearer option and the existing paper execution UI remain available.
* [Deployment guide](../CLOUD_RUN.md) records the per-email IAP grants and audience setting.

## Key Decisions & Context

Cloud IAP IAM owns the email allowlist. The app verifies the signed assertion for defense in depth. The group shares a demo portfolio and its existing risk controls. Local checks used generated signed assertions and mocked paper handlers to verify access without submitting orders.

## Known Gotchas, Blockers & Environment Issues

Cloud Run and IAM have not been updated. Hosted paper execution requires the deployed service's audited database configuration. Live Google sign-in requires an IAP-enabled revision and an allowed user.

## Next Steps (Handoff Checklist)

* [ ] Deploy the new image, set the IAP audience, and verify one allowed and one unlisted Google account.
