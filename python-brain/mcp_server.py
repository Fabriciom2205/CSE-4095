"""The Monroe Fund - Model Context Protocol (MCP) Server for SEC EDGAR Tools.

Exposes SEC search, filing retrieval, XBRL fundamental fact extraction,
and semantic vector RAG as standardized MCP tools, resources, and prompts
for external agents, IDEs, and orchestrators.
"""

import os
import sys
from pathlib import Path

# Add current directory to path if running directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except ImportError:
    pass

from mcp.server.mcpserver import MCPServer
from google import genai

import sec_client
import filing_rag

# Initialize MCP server
mcp = MCPServer(
    name="the-monroe-fund-sec",
    instructions=(
        "The Monroe Fund SEC EDGAR MCP Server provides direct, programmatic tools "
        "to search EDGAR filings, extract audited US-GAAP XBRL financial facts, "
        "download full 10-K/10-Q text, and run semantic vector RAG across filing sections."
    )
)


@mcp.tool(
    name="sec_cik_lookup",
    description="Maps a stock ticker (e.g. 'AAPL') or company name to its 10-digit zero-padded SEC Central Index Key (CIK)."
)
def sec_cik_lookup(company_name_or_ticker: str) -> str:
    """Finds the 10-digit zero-padded SEC CIK for a given ticker or company name."""
    return sec_client.tool_cik_lookup(company_name_or_ticker)


@mcp.tool(
    name="sec_full_text_search",
    description=(
        "Searches SEC EDGAR full-text search API (EFTS) in real-time for keywords across filings "
        "(10-K, 10-Q, 8-K) with optional date filtering. Useful for instant detection of newly published filings."
    )
)
def sec_full_text_search(query: str, form_type: str = "10-K", start_date: str = "") -> list:
    """Searches SEC EDGAR EFTS API for keywords across filings."""
    return sec_client.tool_full_text_search(query=query, form_type=form_type, start_date=start_date)


@mcp.tool(
    name="sec_fetch_filing_text",
    description="Downloads the raw filing text or HTML document directly from SEC EDGAR archives for a specific company CIK, accession number, and filename."
)
def sec_fetch_filing_text(cik: str, accession_number: str, filename: str) -> str:
    """Downloads raw filing text/HTML from the SEC archive repository."""
    return sec_client.tool_fetch_filing_text(cik=cik, accession_number=accession_number, filename=filename)


@mcp.tool(
    name="sec_get_financial_facts",
    description=(
        "Retrieves structured, audited US-GAAP or IFRS financial facts (e.g. 'Revenues', 'NetIncomeLoss', 'Assets', 'OperatingIncomeLoss') "
        "directly from data.sec.gov for a company CIK. Completely eliminates third-party vendor acquisition costs and aggregation lag."
    )
)
def sec_get_financial_facts(cik: str, concept: str) -> dict:
    """Retrieves structured XBRL financial facts (GAAP/IFRS) from data.sec.gov for a company CIK."""
    return sec_client.tool_get_financial_facts(cik=cik, concept=concept)


@mcp.tool(
    name="sec_query_filing_rag",
    description=(
        "Indexes targeted SEC filing sections (e.g., 'mda', 'risk_factors', 'business', 'financials', or 'key_sections') "
        "into semantic chunks and executes vector similarity search using Gemini embeddings to extract specific disclosures and commentary."
    )
)
def sec_query_filing_rag(
    cik: str,
    accession_number: str,
    filename: str,
    question: str,
    section: str = "key_sections",
    top_k: int = 4
) -> str:
    """Indexes targeted SEC filing sections and performs vector similarity search with Gemini embeddings."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return "Error: GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your .env file."

    client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
    return filing_rag.query_filing_rag(
        cik=cik,
        accession_number=accession_number,
        filename=filename,
        question=question,
        client=client,
        section=section,
        top_k=top_k,
    )


@mcp.resource(
    "sec://filings/{cik}/{accession_number}/{filename}",
    name="sec_filing_document",
    description="Raw SEC EDGAR filing document by CIK, accession number, and filename."
)
def get_sec_filing_resource(cik: str, accession_number: str, filename: str) -> str:
    """Reads raw filing text directly as an MCP resource."""
    return sec_client.tool_fetch_filing_text(cik=cik, accession_number=accession_number, filename=filename)


@mcp.prompt(
    name="analyze_sec_filing",
    description="Guides an LLM through conducting a structured fundamental and risk analysis of a company's recent SEC filing."
)
def prompt_analyze_filing(ticker: str, form_type: str = "10-K") -> list[dict]:
    """Provides a structured multi-step analysis template for evaluating filings."""
    return [
        {
            "role": "user",
            "content": (
                f"Please conduct an in-depth financial and operational assessment for {ticker} using their latest {form_type} filing:\n"
                f"1. Use `sec_cik_lookup` to obtain {ticker}'s CIK.\n"
                f"2. Use `sec_get_financial_facts` to pull structured US-GAAP numbers for 'Revenues' and 'NetIncomeLoss'.\n"
                f"3. Use `sec_full_text_search` to find the most recent {form_type} filing accession number and primary document filename.\n"
                f"4. Use `sec_query_filing_rag` with section='mda' to inspect management's discussion on revenue drivers and margins.\n"
                f"5. Use `sec_query_filing_rag` with section='risk_factors' to identify primary operational and market risks.\n"
                f"6. Synthesize the findings into an investment memo summarizing growth, margin trajectory, and risk vectors."
            )
        }
    ]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="The Monroe Fund - SEC EDGAR MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"], help="MCP transport protocol (default: stdio)")
    parser.add_argument("--host", default="0.0.0.0", help="Host address for HTTP/SSE transport (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transport (default: 8000)")
    args = parser.parse_args()

    print(f"Starting The Monroe Fund SEC MCP Server on {args.transport} transport...", file=sys.stderr)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)
