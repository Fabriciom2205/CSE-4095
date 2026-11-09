import os
import asyncio
import numpy as np
import sec_client
import filing_rag
import agent
import mcp_server


def test_chunking():
    sample_html = """
    <html>
        <head><title>Test Filing</title></head>
        <style>.hide { display:none; }</style>
        <body>
            <h1>Item 1A. Risk Factors</h1>
            <p>Our revenue is subject to macroeconomic fluctuations and currency risks across global markets.</p>
            <p>We face significant competition in AI hardware and software development.</p>
        </body>
    </html>
    """
    chunks = filing_rag.clean_and_chunk_html(sample_html, section="risk_factors", chunk_size=50, chunk_overlap=10)
    assert len(chunks) >= 1
    assert "Risk Factors" in chunks[0]
    assert "<style>" not in chunks[0]
    assert "<p>" not in chunks[0]


def test_section_filtering():
    filing_doc = """
    TABLE OF CONTENTS
    Item 1. Business ........................................ Page 1
    Item 1A. Risk Factors ................................... Page 10
    Item 3. Legal Proceedings ............................... Page 25
    Item 7. Management's Discussion and Analysis ............ Page 30
    Item 8. Financial Statements ............................ Page 50
    Item 15. Exhibits ....................................... Page 90

    ITEM 1. BUSINESS
    The Company designs, manufactures, and markets high-performance computing hardware and autonomous trading systems.

    ITEM 1A. RISK FACTORS
    Risks include cybersecurity breaches, volatile market conditions, regulatory changes, and semiconductor supply constraints.

    ITEM 3. LEGAL PROCEEDINGS
    We are involved in routine patent litigation.

    ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION
    Revenue grew 42% year-over-year driven by institutional adoption of our algorithmic execution engine.

    ITEM 8. FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA
    Consolidated Balance Sheets show cash reserves of $1.2B and zero short-term debt obligations.

    ITEM 15. EXHIBITS, FINANCIAL STATEMENT SCHEDULES
    Exhibit 31.1 Certification
    Exhibit 32.1 Officer Certification
    """
    # Test specific section extraction
    rf = filing_rag.filter_filing_sections(filing_doc, section="risk_factors")
    assert "cybersecurity breaches" in rf
    assert "routine patent litigation" not in rf

    mda = filing_rag.filter_filing_sections(filing_doc, section="mda")
    assert "Revenue grew 42%" in mda
    assert "Exhibit 31.1" not in mda

    # Test key sections aggregate: includes 1, 1A, 7, 8 but strips 3 (legal) and 15 (exhibits)
    all_keys = filing_rag.filter_filing_sections(filing_doc, section="key_sections")
    assert "high-performance computing" in all_keys
    assert "cybersecurity breaches" in all_keys
    assert "Revenue grew 42%" in all_keys
    assert "Consolidated Balance Sheets" in all_keys
    assert "routine patent litigation" not in all_keys
    assert "Exhibit 31.1" not in all_keys


def test_cosine_similarity():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    matrix = np.array([v1, v2], dtype=np.float32)
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    scores = np.dot(matrix, query)
    assert scores[0] == 1.0
    assert scores[1] == 0.0


def test_archive_url_construction():
    cik = "0000320193"
    adsh = "0000320193-23-000106"
    filename = "aapl-20230930.htm"
    clean_cik = cik.lstrip("0")
    clean_adsh = adsh.replace("-", "")
    expected = "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm"
    actual = f"https://www.sec.gov/Archives/edgar/data/{clean_cik}/{clean_adsh}/{filename}"
    assert actual == expected


def test_env_and_branding():
    assert "TheMonroeFund" in sec_client.DEFAULT_USER_AGENT


def test_agent_api_key_validation():
    # Save original env vars
    orig_gemini = os.environ.get("GEMINI_API_KEY")
    orig_google = os.environ.get("GOOGLE_API_KEY")
    try:
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
        try:
            agent.create_sec_agent()
            assert False, "Expected ValueError when no API key is configured"
        except ValueError as e:
            assert "Gemini API key not found" in str(e)

        # Test with mock key passed directly
        chat = agent.create_sec_agent(api_key="mock_key_for_testing")
        assert chat is not None
    finally:
        if orig_gemini:
            os.environ["GEMINI_API_KEY"] = orig_gemini
        if orig_google:
            os.environ["GOOGLE_API_KEY"] = orig_google


async def test_mcp_server():
    # Verify tools are registered
    tools = await mcp_server.mcp.list_tools()
    tool_names = [t.name for t in tools]
    expected_tools = [
        "sec_cik_lookup",
        "sec_full_text_search",
        "sec_fetch_filing_text",
        "sec_get_financial_facts",
        "sec_query_filing_rag",
    ]
    for exp in expected_tools:
        assert exp in tool_names, f"Expected tool {exp} to be registered in MCP server"

    # Verify prompt is registered
    prompts = await mcp_server.mcp.list_prompts()
    prompt_names = [p.name for p in prompts]
    assert "analyze_sec_filing" in prompt_names

    # Test MCP tool invocation via MCP interface
    res = await mcp_server.mcp.call_tool("sec_cik_lookup", {"company_name_or_ticker": "AAPL"})
    assert res.is_error is False
    assert res.structured_content == {"result": "0000320193"}


def test_cache_eviction_bounded():
    filing_rag._filing_indices.clear()
    # Populate cache up to limit
    for i in range(filing_rag.MAX_CACHED_FILINGS):
        filing_rag._filing_indices[f"key_{i}"] = {"chunks": [], "embeddings": np.array([])}

    assert len(filing_rag._filing_indices) == filing_rag.MAX_CACHED_FILINGS

    # Indexing one more filing should evict the oldest entry (key_0)
    filing_rag._filing_indices["key_overflow"] = {"chunks": [], "embeddings": np.array([])}
    if len(filing_rag._filing_indices) > filing_rag.MAX_CACHED_FILINGS:
        filing_rag._filing_indices.pop(next(iter(filing_rag._filing_indices)))

    assert len(filing_rag._filing_indices) == filing_rag.MAX_CACHED_FILINGS
    assert "key_0" not in filing_rag._filing_indices
    assert "key_overflow" in filing_rag._filing_indices
    filing_rag._filing_indices.clear()


if __name__ == "__main__":
    test_chunking()
    test_section_filtering()
    test_cosine_similarity()
    test_archive_url_construction()
    test_env_and_branding()
    test_agent_api_key_validation()
    test_cache_eviction_bounded()
    asyncio.run(test_mcp_server())
    print("All SEC agent & MCP server self-checks passed successfully.")
