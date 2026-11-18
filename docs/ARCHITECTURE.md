# The Monroe Fund — Architecture & Technical Direction

The Monroe Fund prioritizes Python-based agentic financial research: searching and aggregating financial data, exposing tools through MCP, and producing grounded AI-assisted analysis. This document describes the direction and distinguishes existing capabilities from planned work.

---

## 1. Near-Term Scope

* **Python brain:** The Gemini agent calls Python research tools for company lookup, filing search, retrieval, and synthesis. The MCP server exposes the shared tools to MCP clients.
* **MCP:** Maintain and test the SEC MCP server and its research tools, including both supported transports. Expand tools and sources as research needs warrant.
* **Financial data aggregation:** Combine structured financial facts and unstructured filings, with further sources such as Finnhub and Alpaca to be evaluated and integrated as needed. Attribute findings to their sources and validate data quality.
* **Research interface:** The React frontend uses mock data. A Python HTTP API and integration with its Research page are planned.
* **Storage and deployment:** The project Cloud SQL database has pgvector and the filing retrieval tables. Live verification covered building a new index and reusing it with reader-only credentials. The standalone importer can store selected facts and auditor data. Financial-fact tools still query EDGAR live. [PostgreSQL decision](decisions/0003-postgresql-sec-research.md) · [Cloud SQL verification](notes/2026-11-17-cloud-sql-filing-retrieval.md)

```mermaid
flowchart LR
    UI["React Research page with mock data"] -. "planned Python HTTP API" .-> Agent["Python research agent"]
    Client["MCP client"] --> MCP["SEC MCP server"]
    Agent --> Tools["Shared Python research tools"]
    MCP --> Tools
    Agent --> Gemini["Gemini"]
    Tools -->|"Company lookup, latest filings, facts"| SEC["Live SEC EDGAR"]
    Tools --> Retrieval["Filing retrieval"]
    Retrieval -->|"Fetch filing on index miss"| SEC
    Retrieval -->|"Embed queries and new filing chunks"| Gemini
    Retrieval -->|"Read indexes and publish on misses"| CloudSQL["Cloud SQL PostgreSQL with pgvector"]
    Importer["Standalone SEC importer"] -->|"Fetch selected SEC data"| SEC
    Importer -->|"Store imported SEC data"| CloudSQL
```

Filing retrieval uses an in-memory index when both PostgreSQL connections are unset. A configured reader can query existing indexes, and a separate scoped writer can publish indexes on cache misses. When the React Research page is connected, it will call the Python backend, which owns the database connections. [PostgreSQL setup](POSTGRESQL.md#enable-persistent-filing-retrieval)

## 2. Deferred Work

Rust compute, backtesting, streaming, and order execution are deferred. Revisit them if measured workloads or product requirements justify the additional components. [Original architecture](decisions/0001-polyglot-trading-platform-architecture.md) · [Python-first scope decision](decisions/0002-python-first-research-scope.md)

## 3. Development Considerations

Prioritize source attribution, input validation, reliable error handling, and evaluation against real filings. Measure model and embedding cost, retrieval quality, and service performance before adding infrastructure or optimizing. Protect credentials and avoid logging sensitive data. Existing live verification and integration tasks are tracked in [AGENTS.md](../AGENTS.md#active-tasks--backlog).

---

## 6. Well-Architected Development Guidance

The [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework) guides the design, implementation, and operation of this platform. These are design objectives, not claims that the proposed infrastructure or controls already exist. Apply the relevant [project skills](../AGENTS.md#google-cloud-well-architected-framework) to each meaningful change, balancing the pillars against the research system's security, reliability, and cost requirements.

* **Operational excellence:** Automate repeatable builds and deployments; define observable service health, actionable alerts, and recovery procedures. Avoid logging secrets or unnecessary sensitive data.
* **Security, privacy, and compliance:** Limit access to each service and role, protect credentials and research data in transit and at rest, and validate tool inputs and external data. Define audit and retention policies before a shared deployment.
* **Reliability:** Define availability and recovery objectives for each service. Test backups, restoration, reconnects, and failure handling for SEC calls, model requests, and database writes.
* **Cost optimization:** Measure model, embedding, storage, database, and compute usage; right-size resources and set budgets appropriate to the workload. Evaluate savings against reliability and latency needs.
* **Performance optimization:** Set and measure latency, throughput, and capacity targets under representative workloads. Profile bottlenecks, including model and network calls, before optimizing.
* **Sustainability:** Reduce unnecessary computation, model calls, data transfer, and storage; consider regional carbon impact alongside latency, resilience, and data requirements.

For significant changes, record decisions, assumptions, trade-offs, and verification in an ADR or worklog. Establish service-level objectives, recovery targets, and security controls as the relevant services are built and validated.
