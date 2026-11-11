"""The Monroe Fund - MCP server tests.

Exercises every tool, the filing resource and the analysis prompt in-process, then connects
to mcp_server.py as a real MCP client over stdio and streamable-http. Hits SEC EDGAR live;
the RAG tool test also calls Gemini and is skipped without GEMINI_API_KEY.

Usage:
    python test_mcp_server.py
"""

import os
import sys
import time
import socket
import tempfile
import subprocess
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

import mcp_server

SERVER_PATH = Path(__file__).resolve().parent / "mcp_server.py"
EXPECTED_TOOLS = {
    "sec_cik_lookup",
    "sec_full_text_search",
    "sec_fetch_filing_text",
    "sec_get_financial_facts",
    "sec_query_filing_rag",
}
# Apple FY2023 10-K
CIK, ADSH, FILENAME = "0000320193", "0000320193-23-000106", "aapl-20230930.htm"


def _text(result) -> str:
    return "".join(getattr(c, "text", "") for c in result.content)


async def test_registration():
    tools = {t.name: t for t in await mcp_server.mcp.list_tools()}
    assert set(tools) == EXPECTED_TOOLS, f"unexpected tool set: {sorted(tools)}"
    for tool in tools.values():
        assert tool.description, f"{tool.name} has no description"
    assert tools["sec_query_filing_rag"].input_schema["required"] == ["cik", "accession_number", "filename", "question"]

    prompts = [p.name for p in await mcp_server.mcp.list_prompts()]
    assert prompts == ["analyze_sec_filing"]

    templates = [t.uri_template for t in await mcp_server.mcp.list_resource_templates()]
    assert templates == ["sec://filings/{cik}/{accession_number}/{filename}"]


async def test_sec_tools_via_mcp():
    res = await mcp_server.mcp.call_tool("sec_cik_lookup", {"company_name_or_ticker": "apple"})
    assert res.structured_content == {"result": CIK}

    res = await mcp_server.mcp.call_tool("sec_full_text_search", {"query": "artificial intelligence", "form_type": "10-K"})
    assert res.is_error is False
    assert '"adsh"' in _text(res) and '"file_name"' in _text(res)

    res = await mcp_server.mcp.call_tool("sec_get_financial_facts", {"cik": CIK, "concept": "Assets"})
    assert res.is_error is False
    assert '"USD"' in _text(res)

    res = await mcp_server.mcp.call_tool("sec_fetch_filing_text", {"cik": CIK, "accession_number": ADSH, "filename": FILENAME})
    assert res.is_error is False
    assert "Apple Inc." in _text(res)


async def test_invalid_arguments_rejected():
    try:
        await mcp_server.mcp.call_tool("sec_cik_lookup", {})
        assert False, "expected a validation error for a missing required argument"
    except Exception as e:
        assert "company_name_or_ticker" in str(e)


async def test_filing_resource():
    contents = list(await mcp_server.mcp.read_resource(f"sec://filings/{CIK}/{ADSH}/{FILENAME}"))
    assert len(contents) == 1
    assert "Apple Inc." in contents[0].content


async def test_analysis_prompt():
    prompt = await mcp_server.mcp.get_prompt("analyze_sec_filing", {"ticker": "MSFT", "form_type": "10-Q"})
    assert [m.role for m in prompt.messages] == ["user"]
    body = prompt.messages[0].content.text
    assert "MSFT" in body and "10-Q" in body
    # Every tool the prompt tells the model to use must exist on the server
    for tool in ("sec_cik_lookup", "sec_get_financial_facts", "sec_full_text_search", "sec_query_filing_rag"):
        assert tool in body and tool in EXPECTED_TOOLS


async def test_filing_rag_via_mcp():
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("  skipped test_filing_rag_via_mcp: no Gemini API key")
        return
    res = await mcp_server.mcp.call_tool("sec_query_filing_rag", {
        "cik": CIK, "accession_number": ADSH, "filename": FILENAME,
        "question": "supply chain risks", "section": "risk_factors", "top_k": 1,
    })
    assert res.is_error is False
    assert _text(res).startswith("[Excerpt 1 | Similarity:")


async def _exercise_client(session: ClientSession):
    """Runs the handshake and one live tool call the way an external agent or IDE would."""
    init = await session.initialize()
    assert init.server_info.name == "the-monroe-fund-sec"
    tools = await session.list_tools()
    assert {t.name for t in tools.tools} == EXPECTED_TOOLS
    res = await session.call_tool("sec_cik_lookup", {"company_name_or_ticker": "AAPL"})
    assert res.structured_content == {"result": CIK}

    res = await session.call_tool("sec_fetch_filing_text", {"cik": CIK, "accession_number": ADSH, "filename": "missing.htm"})
    assert res.is_error is True


async def test_stdio_transport():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)], cwd=str(SERVER_PATH.parent))
    with anyio.fail_after(60):
        async with stdio_client(params, errlog=open(os.devnull, "w")) as (read, write):
            async with ClientSession(read, write) as session:
                await _exercise_client(session)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.3)
    return False


async def test_streamable_http_transport():
    port = _free_port()
    # Server logs go to a file: an unread pipe fills up and stalls the server mid-request
    with tempfile.TemporaryFile("w+") as log:
        proc = subprocess.Popen(
            [sys.executable, str(SERVER_PATH), "--transport", "streamable-http", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(SERVER_PATH.parent), stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            assert _wait_for_port(port), f"server did not open port {port}"
            with anyio.fail_after(60):
                async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read, write, *_):
                    async with ClientSession(read, write) as session:
                        await _exercise_client(session)
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    for test in (
        test_registration,
        test_sec_tools_via_mcp,
        test_invalid_arguments_rejected,
        test_filing_resource,
        test_analysis_prompt,
        test_filing_rag_via_mcp,
        test_stdio_transport,
        test_streamable_http_transport,
    ):
        anyio.run(test)
        print(f"  passed {test.__name__}")
    print("All MCP server tests passed successfully.")
