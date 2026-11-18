# SEC research on PostgreSQL and Cloud SQL

To connect your local backend to the existing project database and run smoke tests, follow the [local setup guide](LOCAL_SETUP.md). This page covers schema administration, ingestion, and deployment.

Use PostgreSQL 15 or newer. The [initial migration](../db/migrations/001_sec.sql) creates the SEC schema for the standalone importer and [research queries](../db/research.sql). The optional [filing retrieval migration](../db/migrations/002_filing_retrieval.sql) enables PostgreSQL-backed semantic search in the agent and MCP tools.

## Local database

Set the standard libpq connection variables for the database you created. Use a prompt for migration credentials and a protected [password file](https://www.postgresql.org/docs/current/libpq-pgpass.html) for unattended imports. The importer uses `PGDATABASE` as a database name and accepts the other standard `PG*` settings.

```bash
export PGHOST=127.0.0.1 PGPORT=5432 PGDATABASE=monroe_fund PGUSER=postgres
psql -X -v ON_ERROR_STOP=1 -f db/migrations/001_sec.sql
psql -X -v ON_ERROR_STOP=1 -f db/tests/sec.sql
```

Install the existing Python requirements and set `SEC_USER_AGENT` with a real contact address. Choose an SEC-listed ticker and run a batch from the repository root once the writer account is configured.

```bash
read -r -p "Company ticker: " TICKER
PGUSER=sec_writer python python-brain/ingest_sec.py "$TICKER" --latest-auditor
PGUSER=sec_writer python python-brain/ingest_sec.py "$TICKER" us-gaap:Assets us-gaap:NetIncomeLoss
psql -X -c "SELECT id, label FROM sec.node WHERE kind = 'company';"
```

Run the sample queries with an actual company node ID and a filing date cutoff:

```bash
PGUSER=sec_reader psql -X -v ON_ERROR_STOP=1 -v company_id=1 -v as_of=2025-12-31 -f db/research.sql
```

The importer reads selected Company Facts histories with exact decimal parsing. It preserves differing observations and can replay a batch without duplicating assertions. The optional auditor load reads the latest original 10-K only. Historical auditor changes require ingesting historical filings. Auditor keys currently normalize only whitespace and case, so firm aliases may need reconciliation. The [SEC Company Facts API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) covers standard tags that apply to the whole filing entity. Use the [Financial Statement and Notes Data Sets](https://www.sec.gov/data-research/sec-markets-data/financial-statement-notes-data-sets) and their dimension metadata for a future segment loader. Retain the full dimension context, including every axis and member, rather than matching on a display label.

## Enable persistent filing retrieval

With your existing PostgreSQL connection settings or Cloud SQL Auth Proxy, run migration 002 as the migration administrator after migration 001. Cloud SQL provides pgvector as the `vector` extension. A local PostgreSQL installation needs the pgvector extension files installed. Migration 002 uses the extension in the `public` schema. [Cloud SQL extension support](https://docs.cloud.google.com/sql/docs/postgres/extensions) · [pgvector installation](https://github.com/pgvector/pgvector#installation)

```bash
psql -X -v ON_ERROR_STOP=1 -f db/migrations/002_filing_retrieval.sql
python -m pip install -r python-brain/requirements.txt
```

In `psql`, use the existing `sec_reader` role or create it with `CREATE ROLE sec_reader LOGIN;` and `\password sec_reader`. Set up a dedicated writer for the derived filing index.

```sql
CREATE ROLE sec_index_writer LOGIN;
\password sec_index_writer
GRANT USAGE ON SCHEMA sec TO sec_reader, sec_index_writer;
GRANT SELECT ON sec.filing_retrieval_index, sec.filing_retrieval_chunk TO sec_reader;
GRANT INSERT ON sec.filing_retrieval_index, sec.filing_retrieval_chunk TO sec_index_writer;
GRANT SELECT (id) ON sec.filing_retrieval_index TO sec_index_writer;
```

Configure the agent and MCP process using `.env` or environment variables. These examples use the proxy port from the Cloud SQL setup below. Store passwords in a protected password file or inject connection settings from a secret store.

```dotenv
SEC_RAG_READ_DSN=host=127.0.0.1 port=5433 dbname=monroe_fund user=sec_reader
SEC_RAG_WRITE_DSN=host=127.0.0.1 port=5433 dbname=monroe_fund user=sec_index_writer
```

The first search for a filing and section fetches the document from EDGAR, embeds the chunks, and publishes the index in one transaction. Later searches for the same filing, section, model, and chunking version embed only the question. Concurrent misses can repeat embedding requests before a single index commits. With only the reader configured, a missing index returns an error. With both settings unset, retrieval uses the in-memory index. The agent still resolves the latest filing via EDGAR and reads financial facts from EDGAR.

From the repository root, run one check after setting up database access, Google Cloud ADC, and the SEC contact. Replace `TICKER` with an SEC-listed ticker.

```bash
python python-brain/init.py --postgres TICKER
```

This checks SEC EDGAR, Gemini, and the PostgreSQL reader. It also requires an excerpt from the latest 10-K through the agent's shared MCP filing tool. A missing Business-section index exercises the writer and stores the resulting index. A previously indexed filing exercises the reader. The regular `init.py` check uses read-only PostgreSQL queries when `SEC_RAG_READ_DSN` is configured. A missing retrieval table means migration 002 needs to be applied. A permissions error means the configured role needs the grants above.

Use the following test on a disposable database after applying both migrations and the grants. Point both test settings at the disposable database. The tests add fixture rows.

```bash
SEC_RAG_TEST_READ_DSN='host=127.0.0.1 dbname=monroe_rag_test user=sec_reader' \
SEC_RAG_TEST_WRITE_DSN='host=127.0.0.1 dbname=monroe_rag_test user=sec_index_writer' \
python -m unittest discover -s python-brain -p 'test_filing_store.py'
```

### Runtime credentials in Secret Manager

For a Cloud Run deployment, enable the Secret Manager API and store two libpq connection strings as separate secrets, one for `sec_reader` and one for `sec_index_writer`. Include the password for each login in its secret. When using Cloud Run's public IP Cloud SQL integration, use the attached instance's socket path, `host=/cloudsql/PROJECT:REGION:INSTANCE`. Reference pinned secret versions as the service's `SEC_RAG_READ_DSN` and `SEC_RAG_WRITE_DSN` environment variables. Grant the backend service account Secret Manager Secret Accessor on those two secrets and Cloud SQL Client for the instance connection. Keep the migration administrator credential separate from the runtime secrets. [Cloud Run secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets) · [Cloud Run to Cloud SQL](https://docs.cloud.google.com/sql/docs/postgres/connect-run)

For local development through the Cloud SQL Auth Proxy, keep separate host and port settings for the proxy and use a protected libpq password file. The Python backend owns both database connections. The browser calls the backend.

## Create and manage Cloud SQL

1. In the Google Cloud console, choose a billing-enabled project, enable the Cloud SQL Admin API, and create a **Cloud SQL for PostgreSQL** instance in the region where the research service will run. Select PostgreSQL 15 or newer, enable automated backups, point-in-time recovery and deletion protection, then create the `monroe_fund` database under **Databases**. Choose an instance size for the expected data and query load. [Create a PostgreSQL instance](https://docs.cloud.google.com/sql/docs/postgres/create-instance)
2. For a development instance you need to reach from a laptop, use the public IP path with the Cloud SQL Auth Proxy and leave authorized networks empty. Give your Google identity **Cloud SQL Client** and install the v2 proxy. For private IP, run the proxy on a host with a path to the instance's VPC and pass `--private-ip`. The proxy handles the encrypted connection to Cloud SQL. A separate PostgreSQL login still controls database access in the steps below. [Connect using the Cloud SQL Auth Proxy](https://docs.cloud.google.com/sql/docs/postgres/connect-auth-proxy)
3. Copy the instance connection name from the instance overview. Start the proxy in one terminal and apply the migration from another.

```bash
gcloud auth application-default login
cloud-sql-proxy --address 127.0.0.1 --port 5433 PROJECT:REGION:INSTANCE
```

```bash
export PGHOST=127.0.0.1 PGPORT=5433 PGDATABASE=monroe_fund PGUSER=postgres
psql -X -W -v ON_ERROR_STOP=1 -f db/migrations/001_sec.sql
psql -X -W -v ON_ERROR_STOP=1
```

4. In the administrator's `psql` session, create separate PostgreSQL logins and scope their grants. Use `\password` to set each password interactively. Keep ownership and future migration rights with the administrator or a dedicated migration role.

```sql
CREATE ROLE sec_reader LOGIN;
CREATE ROLE sec_writer LOGIN;
\password sec_reader
\password sec_writer
GRANT USAGE ON SCHEMA sec TO sec_reader, sec_writer;
GRANT SELECT ON sec.company, sec.filing, sec.fact, sec.node, sec.reported_triple TO sec_reader;
GRANT SELECT, INSERT ON sec.company, sec.filing, sec.fact, sec.node, sec.triple TO sec_writer;
GRANT UPDATE (ticker, name) ON sec.company TO sec_writer;
GRANT UPDATE (label, cik) ON sec.node TO sec_writer;
GRANT USAGE ON SEQUENCE sec.node_id_seq, sec.triple_id_seq TO sec_writer;
REVOKE EXECUTE ON FUNCTION sec.auditor_history(date), sec.subsidiaries(bigint, date) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION sec.auditor_history(date), sec.subsidiaries(bigint, date) TO sec_reader;
```

5. Use those logins for the local import and query commands above without changing the proxy host or port. If you later deploy the Python reader to Cloud Run, use a dedicated service account with **Cloud SQL Client**, attach the Cloud SQL instance to the service, and use the Unix socket at `/cloudsql/PROJECT:REGION:INSTANCE` for the public IP proxy path. Put the database password in Secret Manager and grant access only to that secret. For private IP, configure Cloud Run VPC connectivity and follow the private IP connection path. Run ingestion separately with the writer login. [Connect from Cloud Run](https://docs.cloud.google.com/sql/docs/postgres/connect-run) · [Use secrets with Cloud Run](https://docs.cloud.google.com/run/docs/configuring/services/secrets)
6. Use the instance's monitoring dashboard to watch disk usage, CPU and connections. Set alerts at a level with time to act, track costs against a project budget, and test point-in-time recovery to a separate instance before relying on it for recovery. [Cloud SQL monitoring](https://docs.cloud.google.com/sql/docs/postgres/monitor-instance) · [Point-in-time recovery](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/pitr)

If you already populated a local database, export it with `pg_dump -Fc -n sec -f sec.dump` using the local connection settings. After starting the proxy, switch to the Cloud SQL connection settings and restore into an empty database with `pg_restore --exit-on-error --single-transaction --no-owner --no-privileges -d monroe_fund sec.dump` in place of applying the exported migrations. If the dump includes the filing retrieval tables, create the `vector` extension in `public` in the destination database before restoring. Apply the reader and writer grants after restoring. [Cloud SQL export and import with pg_dump](https://docs.cloud.google.com/sql/docs/postgres/import-export/import-export-dmp)

Apply each new migration explicitly as the migration role and update grants as needed. The reader has access to reported assertions through a filtered view. LLM-extracted assertions require same-filing evidence and confidence at insert time, and are excluded from the reader view. Evidence references establish provenance, while a future review workflow must verify that the chunk actually supports the assertion before enabling it in research.
