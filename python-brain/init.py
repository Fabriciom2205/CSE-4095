"""The Monroe Fund - Python Brain Environment & Health Check.

Verifies that the intelligence tier is ready to run: Python version, installed
dependencies, .env configuration, module imports, agent and MCP server wiring,
and (unless --offline) live connectivity to SEC EDGAR, Gemini, and configured PostgreSQL.

Usage:
    python init.py              # full check, including live API calls
    python init.py --offline    # skip all network checks
    python init.py --postgres TICKER  # require PostgreSQL and search a real filing

Exits with status 1 if any check fails, so it can gate CI or container startup.
"""

import os
import re
import sys
import asyncio
import logging
import argparse
import importlib
from importlib import metadata
from pathlib import Path

BRAIN_DIR = Path(__file__).resolve().parent
REPO_ROOT = BRAIN_DIR.parent
sys.path.insert(0, str(BRAIN_DIR))

# google-genai 3.x requires Python 3.11+
MIN_PYTHON = (3, 11)
BRAIN_MODULES = ["sec_client", "filing_rag", "market_data", "agent", "mcp_server"]
REQUIRED_ENV = ["GOOGLE_CLOUD_PROJECT", "SEC_USER_AGENT"]
# Optional: without a key, only that provider's market data tools are unavailable
MARKET_DATA_KEYS = {"massive": "MASSIVE_API_KEY", "finnhub": "FINNHUB_API_KEY"}
# Declared in .env.example for other tiers; python-brain does not read them yet
FUTURE_ENV = ["ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY", "DATABASE_URL"]

PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"
_results = []


def _redact(text: str) -> str:
    """Removes legacy API keys from error text and truncates long payloads."""
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        key = os.getenv(name)
        if key:
            text = text.replace(key, "***")
    text = " ".join(text.split())
    return text if len(text) <= 240 else text[:237] + "..."


def _describe(error: Exception) -> str:
    """Formats an exception, preferring the short message google-genai API errors carry over their raw JSON."""
    message = getattr(error, "message", None) or str(error)
    code = getattr(error, "code", None)
    return f"{type(error).__name__}{f' {code}' if code else ''}: {message}"


def _run(name: str, check, *args):
    """Executes a check returning (status, detail) and records the result; any exception is a FAIL."""
    try:
        status, detail = check(*args)
    except Exception as e:
        status, detail = FAIL, _describe(e)
    _results.append(status)
    print(f"  [{status}] {name}" + (f" - {_redact(detail)}" if detail else ""))


def _version_tuple(version: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


# ------------------------------------------------------------------------------
# Environment checks
# ------------------------------------------------------------------------------

def check_python_version():
    current = ".".join(str(v) for v in sys.version_info[:3])
    if sys.version_info[:2] < MIN_PYTHON:
        return FAIL, f"Python {current} found, {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required"
    return PASS, f"Python {current} ({sys.executable})"


def check_dependency(package: str, min_version: str):
    try:
        installed = metadata.version(package)
    except metadata.PackageNotFoundError:
        return FAIL, "not installed (run: pip install -r requirements.txt)"
    if min_version and _version_tuple(installed) < _version_tuple(min_version):
        return FAIL, f"{installed} installed, >={min_version} required"
    return PASS, installed


def _read_requirements() -> list[tuple[str, str]]:
    """Parses `name>=version` lines from requirements.txt."""
    requirements = []
    for line in (BRAIN_DIR / "requirements.txt").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name, _, min_version = line.partition(">=")
        requirements.append((name.partition("[")[0].strip(), min_version.strip()))
    # shortcut: only understands `>=` pins, upgrade to packaging.requirements if other specifiers are added
    return requirements


def check_env_file():
    from dotenv import load_dotenv, find_dotenv
    env_path = find_dotenv()
    if not env_path:
        return WARN, "no .env found; relying on system environment variables (cp .env.example .env)"
    load_dotenv(env_path)
    return PASS, env_path


def _placeholder_values() -> dict:
    """Loads the template values from .env.example that mark a key as not yet filled in."""
    from dotenv import dotenv_values
    example = REPO_ROOT / ".env.example"
    if not example.exists():
        return {}
    return {k: v for k, v in dotenv_values(example).items() if v and "your_" in v}


def check_env_var(name: str, placeholders: dict):
    value = os.getenv(name, "")
    if not value:
        if name == "SEC_USER_AGENT":
            return WARN, "not set; sec_client falls back to its built-in default contact"
        return FAIL, "not set"
    if placeholders.get(name) == value:
        # SEC still answers a placeholder contact, so it is a compliance warning rather than a broken setup
        return (WARN if name == "SEC_USER_AGENT" else FAIL), "still the placeholder value from .env.example"
    if name == "SEC_USER_AGENT" and "@" not in value:
        return FAIL, "SEC requires a contact email, e.g. 'TheMonroeFund you@example.com'"
    return PASS, "set"


def check_future_env_var(name: str, placeholders: dict):
    value = os.getenv(name, "")
    state = "set" if value and placeholders.get(name) != value else "not set"
    return SKIP, f"{state}; not used by python-brain yet"


def check_market_data_key(provider: str):
    import market_data
    if market_data.api_key(provider):
        return PASS, "set"
    return SKIP, "not set; its market data tools report the missing key"


# ------------------------------------------------------------------------------
# Code wiring checks (offline)
# ------------------------------------------------------------------------------

def check_import(module: str):
    importlib.import_module(module)
    return PASS, ""


def check_mcp_registration():
    import mcp_server
    tools = asyncio.run(mcp_server.mcp.list_tools())
    prompts = asyncio.run(mcp_server.mcp.list_prompts())
    templates = asyncio.run(mcp_server.mcp.list_resource_templates())
    if not tools:
        return FAIL, "no tools registered"
    missing_docs = [t.name for t in tools if not t.description]
    if missing_docs:
        return FAIL, f"tools without descriptions: {', '.join(missing_docs)}"
    return PASS, f"{len(tools)} tools, {len(prompts)} prompts, {len(templates)} resource templates"


def check_agent_construction():
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        return SKIP, "no Google Cloud project"
    import agent
    chat = agent.create_sec_agent()
    return (PASS, "") if chat is not None else (FAIL, "create_sec_agent() returned None")


# ------------------------------------------------------------------------------
# Live connectivity checks
# ------------------------------------------------------------------------------

def check_sec_cik_lookup():
    import sec_client
    cik = sec_client.tool_cik_lookup("AAPL")
    if cik != "0000320193":
        return FAIL, f"expected 0000320193 for AAPL, got {cik!r}"
    return PASS, "www.sec.gov reachable, AAPL -> 0000320193"


def check_sec_full_text_search():
    import sec_client
    hits = sec_client.tool_full_text_search("artificial intelligence", form_type="10-K")
    if not hits:
        return FAIL, "efts.sec.gov returned no hits"
    incomplete = [k for k in ("cik", "adsh", "form", "file_name") if not hits[0].get(k)]
    if incomplete:
        return FAIL, f"first hit missing fields: {', '.join(incomplete)}"
    return PASS, f"efts.sec.gov reachable, {len(hits)} hits"


def check_sec_financial_facts():
    import sec_client
    facts = sec_client.tool_get_financial_facts("0000320193", "Assets")
    if not facts.get("units"):
        return FAIL, "data.sec.gov returned no 'Assets' facts for AAPL"
    return PASS, "data.sec.gov reachable, XBRL facts parsed"


def check_massive():
    import market_data
    if not market_data.api_key("massive"):
        return SKIP, "MASSIVE_API_KEY not set"
    bar = market_data.massive_previous_close("AAPL")
    return PASS, f"api.massive.com reachable, AAPL closed at {bar['close']} on {bar['date']}"


def check_finnhub():
    import market_data
    if not market_data.api_key("finnhub"):
        return SKIP, "FINNHUB_API_KEY not set"
    quote = market_data.finnhub_quote("AAPL")
    return PASS, f"finnhub.io reachable, AAPL quote {quote['price']} as of {quote['as_of']}"


def check_gemini_embeddings():
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        return SKIP, "no Google Cloud project"
    import google_client
    import filing_rag
    client = google_client.create_client()
    resp = client.models.embed_content(
        model=filing_rag.DEFAULT_EMBEDDING_MODEL, contents=["health check"],
        config={"output_dimensionality": filing_rag.EMBEDDING_DIMENSIONS},
    )
    dimensions = len(resp.embeddings[0].values)
    if dimensions != filing_rag.EMBEDDING_DIMENSIONS:
        return FAIL, f"expected {filing_rag.EMBEDDING_DIMENSIONS} dimensions, got {dimensions}"
    return PASS, f"{filing_rag.DEFAULT_EMBEDDING_MODEL}, {dimensions} dimensions"


def check_agent_chat():
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        return SKIP, "no Google Cloud project"
    import agent
    chat = agent.create_sec_agent()
    # Validates ADC, the chat model, and that Gemini accepts every tool declaration
    resp = chat.send_message("Health check: reply with the single word OK. Do not call any tools.")
    if not resp.text:
        return FAIL, "empty response from Gemini"
    return PASS, f"model replied {resp.text.strip()[:20]!r}"


def check_postgres(ticker=None):
    import numpy as np
    import filing_rag
    import filing_store

    read_dsn = os.getenv("SEC_RAG_READ_DSN")
    if not read_dsn:
        if ticker or os.getenv("SEC_RAG_WRITE_DSN"):
            return FAIL, "set SEC_RAG_READ_DSN for PostgreSQL filing retrieval"
        return SKIP, "SEC_RAG_READ_DSN unset; filing retrieval uses memory"

    key = ("0000000001", "0000000001-00-000001", "readiness.htm", "business",
           filing_rag.DEFAULT_EMBEDDING_MODEL, filing_rag.EMBEDDING_DIMENSIONS,
           filing_rag.CHUNK_VERSION)
    filing_store.find_index(read_dsn, key)
    vector = np.zeros(filing_rag.EMBEDDING_DIMENSIONS, dtype=np.float32)
    vector[0] = 1.0
    filing_store.search_index(read_dsn, 0, vector, 1)
    if ticker is None:
        return PASS, "filing index and vector queries available through the reader"

    import agent
    result = agent.sec_query_filing_rag(ticker, "What does this company do?", section="business", top_k=1)
    if not result["data"]["excerpts"].startswith("[Excerpt 1 |"):
        return FAIL, "the PostgreSQL filing search returned no excerpts"
    return PASS, f"agent filing tool retrieved a PostgreSQL excerpt for {result['data']['ticker']}"


def main() -> int:
    parser = argparse.ArgumentParser(description="The Monroe Fund - python-brain health check")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="skip all network checks")
    mode.add_argument("--postgres", metavar="TICKER", help="require PostgreSQL and search the latest 10-K")
    args = parser.parse_args()
    # Silence per-request httpx / google-genai INFO logs so only check results are printed
    logging.disable(logging.INFO)

    print("The Monroe Fund - python-brain health check\n")

    print("Environment")
    _run("Python version", check_python_version)
    for package, min_version in _read_requirements():
        _run(f"Package {package}", check_dependency, package, min_version)
    if FAIL in _results:
        print("\nMissing dependencies; install them before running the remaining checks.")
        return 1

    _run(".env file", check_env_file)
    placeholders = _placeholder_values()
    for name in REQUIRED_ENV:
        _run(name, check_env_var, name, placeholders)
    for provider, name in MARKET_DATA_KEYS.items():
        _run(name, check_market_data_key, provider)
    for name in FUTURE_ENV:
        _run(name, check_future_env_var, name, placeholders)

    print("\nModules")
    for module in BRAIN_MODULES:
        _run(f"import {module}", check_import, module)
    _run("MCP server registration", check_mcp_registration)
    _run("SEC agent construction", check_agent_construction)

    print("\nLive connectivity")
    if args.offline:
        print("  [SKIP] --offline set")
    else:
        _run("PostgreSQL filing retrieval", check_postgres, args.postgres)
        _run("SEC company tickers", check_sec_cik_lookup)
        _run("SEC full-text search", check_sec_full_text_search)
        _run("SEC XBRL financial facts", check_sec_financial_facts)
        _run("Massive previous close", check_massive)
        _run("Finnhub quote", check_finnhub)
        _run("Gemini embeddings", check_gemini_embeddings)
        _run("Gemini agent chat", check_agent_chat)

    counts = {status: _results.count(status) for status in (PASS, WARN, FAIL, SKIP)}
    print(f"\nSummary: {counts[PASS]} passed, {counts[WARN]} warnings, {counts[FAIL]} failed, {counts[SKIP]} skipped")
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
