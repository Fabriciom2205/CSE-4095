import os
from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except ImportError:
    pass

import sec_client
import filing_rag

# Re-export SEC client tools for direct agent invocation and backward compatibility
tool_cik_lookup = sec_client.tool_cik_lookup
tool_full_text_search = sec_client.tool_full_text_search
tool_fetch_filing_text = sec_client.tool_fetch_filing_text
tool_get_financial_facts = sec_client.tool_get_financial_facts


def create_sec_agent(api_key: str = None, model: str = "gemini-2.5-flash"):
    """Instantiates a Gemini agent equipped with SEC search and RAG retrieval tools."""
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError(
            "Gemini API key not found. Please set GEMINI_API_KEY in your .env file or pass api_key to create_sec_agent()."
        )
    client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})

    def tool_query_filing_vector_database(cik: str, accession_number: str, filename: str, question: str, section: str = "key_sections") -> str:
        """Indexes targeted SEC filing sections into semantic chunks and performs vector similarity search with gemini-embedding-2.
        
        Args:
            cik: 10-digit zero-padded CIK number.
            accession_number: Filing accession number (adsh).
            filename: Target HTML or text document name.
            question: Specific question or query to locate relevant excerpts.
            section: Section target: 'business' (Item 1), 'risk_factors' (Item 1A), 'mda' (Item 7), 'financials' (Item 8), or 'key_sections' (all four, skipping legal disclosures and exhibits).
        """
        return filing_rag.query_filing_rag(cik, accession_number, filename, question, client=client, section=section)

    tools = [
        tool_cik_lookup,
        tool_full_text_search,
        tool_fetch_filing_text,
        tool_get_financial_facts,
        tool_query_filing_vector_database,
    ]

    system_instruction = (
        "You are The Monroe Fund's expert financial research agent with direct programmatic access to SEC EDGAR. "
        "Use your tools to find CIK numbers, search filings via EFTS, retrieve structured XBRL facts, "
        "and use the vector database tool to inspect large filings efficiently. "
        "Always cite the accession number, filing date, and source facts."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        temperature=0.2,
    )

    chat = client.chats.create(model=model, config=config)
    return chat
