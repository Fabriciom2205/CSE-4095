# Local setup and database testing

This walkthrough runs the Python backend on your machine against the existing project Cloud SQL database. You can test the database and agent from a terminal without running the React frontend. To provision a separate database or apply migrations, use the [PostgreSQL administration guide](POSTGRESQL.md).

## 1. Install the tools and Python dependencies

Install Python 3.11 or newer, the Google Cloud CLI, the Cloud SQL Auth Proxy v2, and the PostgreSQL command-line client (`psql`). The commands below use Bash on Linux or macOS. [Google Cloud CLI installation](https://docs.cloud.google.com/sdk/docs/install) · [Cloud SQL Auth Proxy installation](https://docs.cloud.google.com/sql/docs/postgres/connect-auth-proxy)

From the repository root, create a virtual environment and copy the environment template if you have yet to create `.env`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python-brain/requirements.txt
test -e .env || cp .env.example .env
```

In `.env`, set `GOOGLE_CLOUD_PROJECT` to the project used for Gemini and `SEC_USER_AGENT` to your organization name and a real email address. Keep `GOOGLE_CLOUD_LOCATION=global` and `GEMINI_EMBEDDING_MODEL=gemini-embedding-2` to match the verified configuration. The embedding model is part of the index key, so changing it can require a fresh index.

## 2. Get access and start the proxy

Ask the project admin for the Cloud SQL instance connection name for `mfund-instance`, Cloud SQL Client access, and permission to call Gemini through Vertex AI. Ask for the PostgreSQL `sec_reader` credential through the team's secure channel. You also need `sec_index_writer` if you plan to build missing indexes. The existing project database already has the required migrations and grants. [Connect using the Cloud SQL Auth Proxy](https://docs.cloud.google.com/sql/docs/postgres/connect-auth-proxy) · [Vertex AI authentication](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/gcp-auth)

Sign in with the Google account that has access, then start the proxy. Replace `PROJECT:REGION:INSTANCE` with the full connection name and leave this terminal running.

```bash
gcloud auth application-default login
cloud-sql-proxy --address 127.0.0.1 --port 5433 PROJECT:REGION:INSTANCE
```

The proxy authenticates to Google Cloud. PostgreSQL authenticates the database login separately.

## 3. Configure local database credentials

In a second terminal, create or open `~/.pgpass` and restrict its permissions.

```bash
touch ~/.pgpass
chmod 600 ~/.pgpass
```

Add the applicable lines in a local editor, replacing the placeholders with the issued passwords. Preserve any unrelated entries. The first matching row wins, so put specific entries above wildcard entries. Escape literal colons as `\:` and backslashes as `\\` in the password field. [PostgreSQL password file format](https://www.postgresql.org/docs/current/libpq-pgpass.html)

```text
127.0.0.1:5433:monroe_fund:sec_reader:<reader-password>
127.0.0.1:5433:monroe_fund:sec_index_writer:<writer-password>
```

Uncomment the corresponding settings in the repository-root `.env`. Keeping the writer setting commented out gives you reader-only operation. Match the host, port, database, and usernames to `.pgpass`.

```dotenv
SEC_RAG_READ_DSN=host=127.0.0.1 port=5433 dbname=monroe_fund user=sec_reader
SEC_RAG_WRITE_DSN=host=127.0.0.1 port=5433 dbname=monroe_fund user=sec_index_writer
```

**This is the current local credential setup.** Once the Secret Manager workflow is available, it will change how the backend receives credentials. The planned Cloud Run deployment will inject versioned secrets into the same two DSN settings. Until the local workflow is documented, use the protected password file for development and keep database passwords out of the repository and your command history. [Secret Manager deployment plan](POSTGRESQL.md#runtime-credentials-in-secret-manager)

## 4. Verify the database and the agent

Check the database login and schema independently of Python and Gemini. The query should show `sec_reader`, the pgvector version, and both retrieval table names.

```bash
psql -X -w -v ON_ERROR_STOP=1 "host=127.0.0.1 port=5433 dbname=monroe_fund user=sec_reader" \
  -c "SELECT current_user, (SELECT extversion FROM pg_extension WHERE extname = 'vector') AS pgvector, to_regclass('sec.filing_retrieval_index') AS filing_index, to_regclass('sec.filing_retrieval_chunk') AS filing_chunks;"
```

From the repository root, activate the virtual environment in this terminal and run the full health check. Look for `[PASS] PostgreSQL filing retrieval`, along with the SEC and Gemini checks.

```bash
source .venv/bin/activate
python python-brain/init.py
```

To verify that the agent's filing tool can build and reuse an index, try a **10-Q**. Run the following from inside `python-brain` with the virtual environment active. The first command builds the filing index on a miss if the writer is configured. The second disables writes for that invocation. If it returns excerpts, the reader found the stored index in PostgreSQL.

```bash
python -c 'from agent import sec_query_filing_rag; print(sec_query_filing_rag("MSFT", "What drove changes in operating income this quarter?", form="10-Q", section="mda")["data"]["excerpts"])'

SEC_RAG_WRITE_DSN='' python -c 'from agent import sec_query_filing_rag; print(sec_query_filing_rag("MSFT", "What drove changes in operating income this quarter?", form="10-Q", section="mda")["data"]["excerpts"])'
```

## Common setup failures

| Symptom | What to check |
| --- | --- |
| Proxy fails to start or authenticate | Verify the instance connection name, Cloud SQL Client access, and ADC login. If port 5433 is in use, choose a free port and update both DSNs and the password file. |
| `connection refused` | Leave the proxy running and confirm the DSN uses its bound host and port. |
| `no password supplied` | Check mode `0600` and verify the first four password-file fields match the connection. If `PGPASSFILE` is set, libpq uses that file. |
| `password authentication failed` | Check that the password belongs to the requested database role and that password-file escaping is correct. |
| Missing tables or permission denied | Verify that you reached the project database. Ask the database admin to check migration 002 and the scoped grants if the tables or permissions are missing. |
| PostgreSQL check says `SKIP` | Set `SEC_RAG_READ_DSN` in the repository-root `.env`. |
| Reader-only filing check says the index is missing | Run the same ticker, form, and section with the writer enabled first. A newly filed report or a different embedding model can select a different index. |
| Gemini authentication or permission error | Check ADC, `GOOGLE_CLOUD_PROJECT`, and your Vertex AI access. |

For SQL migrations, the standalone importer, or tests that insert fixture rows into a disposable database, see the [PostgreSQL administration guide](POSTGRESQL.md#enable-persistent-filing-retrieval).
