# Worklog: Cloud Run IAP demo revision

* **Date:** 2026-11-25
* **Contributor / Agent:** Codex
* **Branch:** main
* **Status:** Deployed during the IAP trial. The [local demo setup](2026-11-25-local-demo-setup.md) supersedes this plan.

## Objective

Deploy the bundled frontend and API to the IAP-enabled service.

## Changes Implemented

Published the locally verified image to `monroe-services` and deployed digest `sha256:7ea7c1f716a110087801d4550e1a76c95ebb74ffe645948873343a539a5bcc8c`. Revision `monroe-api-00002-nzp` is ready and receives all traffic. The deployment set `MONROE_IAP_AUDIENCE` and preserved the existing Cloud SQL attachment and service configuration.

## Key Decisions & Context

The service-level IAP policy has five individual user grants and no other grants. IAP is enabled and intercepts browser requests.

## Known Gotchas, Blockers & Environment Issues

Both service URLs return an IAP-generated HTTP 502 stating that the Google Account OAuth client ID or secret is empty. Finish external OAuth client setup in the Console before browser verification. The deployed service has no `MONROE_PORTFOLIO_DSN`, so hosted paper order submission still needs audited execution database setup.

## Next Steps (Handoff Checklist)

* [x] Close the IAP demo plan in favor of local operation.
