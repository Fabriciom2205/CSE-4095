# Local setup and database testing

This walkthrough runs the Python backend on your machine against the existing project Cloud SQL database. You can test the database and agent from a terminal. To provision a separate database or apply migrations, use the [PostgreSQL administration guide](POSTGRESQL.md).

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

Optionally, set `MASSIVE_API_KEY` and `FINNHUB_API_KEY` to enable the market data tools. Without a key, only that provider's tools are unavailable, and the health check skips its live check. Obtain the keys through the team's secure channel and keep them out of the repository.

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

## Run the backend tests

From the repository root, with the virtual environment active:

```bash
python -m unittest discover -s python-brain
```

The suite discovers tests under `python-brain/tests/`. PostgreSQL integration tests require disposable test databases. See the [filing index test setup](POSTGRESQL.md#enable-persistent-filing-retrieval).

Run the opt-in SEC and MCP checks from `python-brain/`. These can call EDGAR and Gemini using your configured credentials.

```bash
python -m tests.live.sec_smoke
python -m tests.live.mcp_smoke
python -m tests.live.security_smoke
python -m tests.live.research_benchmark MSFT
```

The research benchmark uses fresh sessions and an in-memory filing index. It checks for both SEC and Finnhub citations and reports cold and warm latency, model usage, and embedding usage. The security smoke check sends synthetic filing passages to the configured Gemini model.

## Portfolio and strategy tools

For Alpaca, set `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY` in your local environment or repository `.env`. The default `ALPACA_BASE_URL` points to paper accounts. Launch Python from `python-brain/` to use the client:

```python
from alpaca_client import get_account, get_orders, get_positions

account = get_account()
positions = get_positions()
orders = get_orders(status="all", limit=50)
```

Positions include quantity, market value, cost basis, and unrealized profit or loss as decimal values when reported. Short quantity and market value are signed. Orders are a bounded page of recent order records. The portfolio tables are provisioned separately. The client returns data to the caller without persisting it. [Portfolio schema](POSTGRESQL.md#portfolio-schema)

To backtest an example over twelve months, set `MASSIVE_API_KEY` and run the following from the repository root. Keep the snapshot and result together to reproduce the run.

```bash
python python-brain/backtest.py capture 2025-01-01 2025-12-31 SPY > bars.json
python python-brain/backtest.py replay bars.json > result.json
```

The example uses a fixed universe, a 20-session moving average, a 25% allocation, and a 10% stop evaluated at the close. Orders generated at a close attempt to fill at the next session's open. The output contains the snapshot hash, fills, closing equity, and drawdown. The replay uses raw daily bars, and capture rejects windows with splits or stock dividends. It assumes the supplied universe was chosen before the window. It models neither cash distributions nor execution costs.

## Portfolio proposals

Use `agent.generate_proposal(prompt, limits=..., peak_equity=...)` from a trusted local Python caller. Supply `risk.RiskLimits` and a positive `Decimal` peak from your account's equity history. Current equity can increase that peak. The proposal session sends equity, the peak, and signed market values to the configured model. The regular research agent and MCP server do not expose these private tools.

The schema accepts up to ten distinct symbols with combined target weights at most one. Each target includes a rationale, SEC accessions, a market timestamp with timezone, and confidence. Validation checks the projected dollar exposure of each named target and retains unlisted holdings. It measures the largest hypothetical dollar change for the order notional cap. A sector cap uses the issuer's EDGAR SIC code grouped by official industry division and blocks when a required classification is missing. This is an issuer-level grouping. Funds and other instruments are excluded when their issuer classification is unavailable, and the app has no holdings look-through. [SEC SIC codes](https://www.sec.gov/search-filings/standard-industrial-classification-sic-code-list) · [SIC divisions](https://www.osha.gov/data/sic-manual)

`propose.build_orders` is a separate pure helper that sizes hypothetical whole-share buys from cash. The agent does not call it or receive its quantities.

### Audited paper execution runbook

**Pre-market.** Apply [migration 004 and the portfolio grants](POSTGRESQL.md#audited-paper-execution). Set `MONROE_PORTFOLIO_DSN` for the shared execution database and confirm `ALPACA_BASE_URL=https://paper-api.alpaca.markets`. Configure positive name, gross, order, drawdown, daily count, and daily notional caps in `portfolio.risk_limit`. An optional sector cap uses EDGAR SIC divisions. Seed equity history from verified observations for that account. Operators starting a new tracking interval can deliberately record the current broker observation with `portfolio_agent.py --record-equity`. A baseline recorded today does not recover an earlier peak.

**During the session.** Proposal mode remains the default. Execution accepts only database limits and peak equity. Choose a stable decision key and reuse the exact symbol and prompt on every retry:

```bash
.venv/bin/python python-brain/portfolio_agent.py --execute-paper --symbol NVDA \
  --decision-key paper-check-001 "Evaluate NVDA for a paper target"
```

One shared PostgreSQL account lock serializes executions and reconciliation. Unsettled intents and open broker orders block additional submissions. The daily ledger counts all reserved intents and their limit notionals from midnight New York time, including ambiguous or rejected attempts. Keep other writers off the dedicated paper account during a run. A repeated key returns the original result without calling the model or broker again.

**Halt.** Set `MONROE_EXECUTION_HALT=1` in the runner environment before launching commands. This blocks new runs before provider requests. Stop any already running command separately because environment changes do not propagate to it. Cancel an accepted order in Alpaca if needed. This CLI has no cancel or amend command.

**Post-session.** Run the read-only broker reconciliation command or schedule that command alone on an operator-controlled timer:

```bash
.venv/bin/python python-brain/portfolio_agent.py --reconcile
```

Compare `portfolio.trade` activity IDs and quantities with Alpaca. A terminal order stays unsettled until its recorded fills match the broker's filled quantity. A confirmed 404 can close an unacknowledged intent after 24 hours. An acknowledged order that disappears stays unresolved. An ambiguous submission returns the client order ID and is never retried. [Order lookup](https://docs.alpaca.markets/us/reference/getorderbyclientorderid) · [Fill activity API](https://docs.alpaca.markets/us/reference/getaccountactivitiesbyactivitytype-1)

## Phase 5 HTTP API

Install the repository requirements into the virtual environment. ADK uses the same Google Cloud project and Application Default Credentials as the existing Gemini tools. Configure these settings in the server environment or your local `.env`:

| Setting | Purpose |
| --- | --- |
| `MONROE_API_TOKEN` | A random bearer token you generate. Clients send it in the Authorization header. |
| `MONROE_SESSION_DSN` | An async SQLAlchemy connection URL for a dedicated PostgreSQL session database, for example `postgresql+asyncpg://monroe_sessions@127.0.0.1:5433/monroe_sessions`. ADK initializes its own tables in that database. SQLite file URLs with `sqlite+aiosqlite` work for local evaluation. Create the database file’s parent directory first. |
| `MONROE_SNAPSHOT_DIR` | Optional directory of saved backtest JSON files. The default is `snapshots` relative to the server working directory. |
| `MONROE_PORTFOLIO_READ_DSN` | Read-only PostgreSQL connection for HTTP proposal drawdown checks. Uses the stored peak for the signed-in Alpaca account. [Reader grants](POSTGRESQL.md#http-proposal-equity-history). |
| `MONROE_PEAK_EQUITY` | Operator-supplied historical peak for HTTP proposal drawdown checks when a portfolio reader is absent. |

From the repository root:

```bash
.venv/bin/python -m uvicorn api:app --app-dir python-brain --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` or fetch `/openapi.json` for the typed contract. Application routes are bearer protected. The health route only checks configuration. Keep this single-operator service on loopback for local development. Use TLS for any remote deployment.

### Research voice input

Send up to 4 MiB of recorded audio bytes to authenticated `POST /research/transcribe`. Set the recording's `Content-Type` to `audio/webm`, `audio/ogg`, `audio/mp4`, `audio/wav`, or `audio/mpeg`. The response is `{"transcript":"…"}`. Let the operator review or edit the transcript, then send it as the existing `question` field on `POST /research`. The server sends audio to the configured Gemini service for transcription and keeps no audio file in the application. Only the submitted question becomes part of the research conversation. [Gemini audio formats](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/audio-understanding)

### Shared MCP access

Keep stdio or loopback for local use. For shared access, set `MONROE_MCP_TOKEN` to a separate random bearer credential of at least 32 characters and set `MONROE_MCP_PUBLIC_URL` to the exact HTTPS origin, for example `https://mcp.example.com`. All transport requests must carry `Authorization: Bearer <token>`. Host and browser Origin checks use the configured public origin. The credential represents a trusted operator with access to the research tool set.

Use a private HTTPS reverse proxy forwarding to the loopback server and preserving the public Host. For a direct non-loopback listener, provide both `--tls-cert` and `--tls-key` with the shared settings. Restrict ingress and apply request limits at the deployment edge. Per-user access requires individual identities at that edge.

### Research tables and charts

Ask for a visual in the current question or set the optional `visual` field to `table`, `bar`, or `line`. For example, send this JSON to `POST /research`.

```json
{
  "ticker": "AAPL",
  "question": "Show Apple's revenue and operating income for the last three fiscal years in a table."
}
```

For a chart of the same figures, reuse the response's `session_id` and ask “Plot it.” The optional `visuals` array appears in the JSON response or the SSE `final` event when supported figures are available. It includes a visual kind, column keys, fiscal period rows, units, and cell-level filing sources. Values are decimal strings, missing cells contain `null`, and derived Q4 cells cite their full-year and nine-month inputs. Use the period-end date for the chart's x-axis and the column keys for its series. The current scope is supported balance sheet, income statement, and cash flow lines.

`POST /research` creates a session or continues a returned `session_id`. Send `Accept: text/event-stream` to receive answer deltas and a final event containing the same object as the JSON response. Keep the session ID between turns. `POST /proposals` takes `tickers` and `constraints`, returns validated targets and breach findings, and uses a separate session namespace. Its Alpaca inputs are cached for up to 15 seconds. Alpaca mark freshness is reported as unknown and dated Finnhub quotes older than two minutes are marked stale. Execution remains outside the HTTP API.

To run a backtest, capture an input using the replay CLI above into this directory, for example `snapshots/spy-2025.json`. The request uses the ID `spy-2025` with the strategy settings. The server does not accept a filesystem path.

### Figure disclosures

Ask `POST /research` a question without a ticker to look up disclosures by person or manager:

```json
{"question":"What did Berkshire Hathaway's holdings reports show changed last quarter?"}
```

The research agent and MCP server share `sec_figure_disclosures`. Use `kind: "form4"` for reported ownership transactions, such as Jeff Bezos, or `kind: "13f"` for institutional holdings, such as Berkshire Hathaway or Pershing Square. The tool also accepts a filer’s exact SEC CIK. The Buffett alias refers to Berkshire only in 13F lookups. Form 4 rows include the owner, transaction code, transaction date, and filing date. Original and amended Forms 4 are presented as filed. A 13F compares two consecutive reported quarter-end positions and applies supported amendments. Holdings changes do not reveal the exact trades, prices, or decision maker. Congressional reports use a separate filing system and are outside this SEC tool.

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
| Market data tool reports a missing key, HTTP 401 or 403, or a rate limit | Check `MASSIVE_API_KEY` or `FINNHUB_API_KEY`, and whether the provider plan includes that data and request rate. |

For SQL migrations, the standalone importer, or tests that insert fixture rows into a disposable database, see the [PostgreSQL administration guide](POSTGRESQL.md#enable-persistent-filing-retrieval).
