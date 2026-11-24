# Private Cloud Run backend

The Monroe Fund API runs as `monroe-api` in `us-east1` in project `fintech-showcase-mfund-2026`. The service uses the repository [Dockerfile](../Dockerfile) and runs FastAPI on port 8080. It can scale to zero and is limited to two instances.

## Access

Cloud Run requires a Google identity with permission to invoke the service. For direct HTTPS requests, send the Google identity token in `X-Serverless-Authorization: Bearer …`. For protected application routes, also send the application's bearer token in `Authorization: Bearer …`. The application token is stored in Secret Manager as `monroe-api-token`. [Cloud Run request authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service)

## Runtime

The dedicated `monroe-api` service account can call Gemini and connect to Cloud SQL. It has access to the specific Secret Manager entries referenced by the service. The session DSN points at the `monroe_sessions` database. The SEC reader and index writer DSNs point at `monroe_fund`. Cloud Run connects through the attached instance's Unix socket. The service references fixed secret versions. [Cloud SQL from Cloud Run](https://docs.cloud.google.com/sql/docs/postgres/connect-instance-cloud-run) · [Cloud Run secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets)

Publish future container images to the `monroe-services` Artifact Registry repository in `us-east1`. Update the existing service by digest to retain its Cloud SQL attachment, identity, secret references, and access policy.

```bash
gcloud run services update monroe-api --region=us-east1 \
  --project=fintech-showcase-mfund-2026 \
  --image=us-east1-docker.pkg.dev/fintech-showcase-mfund-2026/monroe-services/monroe-api@IMAGE_DIGEST
```

Verify an authenticated research request after deploying a revision. Run MCP and authorized paper execution separately when needed. Local development remains available through the [systemd services](LOCAL_SETUP.md#start-the-local-services-together).
