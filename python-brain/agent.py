import os
from google import genai
from google.genai import types

import sec_client
import filing_rag


def tool_cik_lookup(company_name_or_ticker: str) -> str:
    """Finds the 10-digit zero-padded SEC CIK for a given ticker or company name.
    
    Args:
        company_name_or_ticker: Stock ticker (e.g., 'AAPL') or company name (e.g., 'Apple Inc').
    """
    return sec_client.tool_cik_lookup(company_name_or_ticker)


def tool_full_text_search(query: str, form_type: str = "10-K", start_date: str = "") -> list:
    """Searches SEC EDGAR full-text search API (EFTS) for keywords across filings.
    
    Args:
        query: Search keywords or phrases (e.g. 'restructuring charges', 'AI infrastructure').
        form_type: Targeted form types (e.g. '10-K', '10-Q', '8-K').
        start_date: Optional start date in YYYY-MM-DD format.
    """
    return sec_client.tool_full_text_search(query=query, form_type=form_type, start_date=start_date)


def tool_fetch_filing_text(cik: str, accession_number: str, filename: str) -> str:
    """Downloads raw filing text/HTML from the SEC archive repository.
    
    Args:
        cik: 10-digit CIK number.
        accession_number: Filing accession number with or without hyphens.
        filename: Document filename from filing index (e.g. 'aapl-20230930.htm').
    """
    return sec_client.tool_fetch_filing_text(cik=cik, accession_number=accession_number, filename=filename)


def tool_get_financial_facts(cik: str, concept: str) -> dict:
    """Retrieves structured XBRL financial facts (GAAP/IFRS) from data.sec.gov for a company CIK.
    
    Args:
        cik: 10-digit zero-padded CIK number.
        concept: US-GAAP or IFRS concept tag (e.g., 'Revenues', 'NetIncomeLoss', 'Assets').
    """
    return sec_client.tool_get_financial_facts(cik=cik, concept=concept)


def create_sec_agent(api_key: str = None, model: str = "gemini-2.5-flash"):
    """Instantiates a Gemini agent equipped with SEC search and RAG retrieval tools."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=key)

    def tool_query_filing_vector_database(cik: str, accession_number: str, filename: str, question: str, section: str = "key_sections") -> str:
        """Indexes targeted SEC filing sections into semantic chunks and performs vector similarity search with gemini-embedding-2.
        
        Args:
            cik: 10-digit zero-padded CIK number.
            accession_number: Filing accession number (adsh).
            filename: Target HTML or text document name.
            question: Specific question or query to locate relevant excerpts.
            section: Section target: 'business' (Item 1), 'risk_factors' (Item 1A), 'mda' (Item 7), 'financials' (Item 8), or 'key_sections' (all four, skipping legal disclosures and exhibits).
        """
        cache_key = f"{cik}_{accession_number}_{filename}_{section}"
        if cache_key not in filing_rag._filing_indices:
            raw_html = sec_client.tool_fetch_filing_text(cik=cik, accession_number=accession_number, filename=filename)
            chunks = filing_rag.clean_and_chunk_html(raw_html, section=section)
            filing_rag.index_filing(cache_key, chunks, client=client)

        results = filing_rag.query_filing_index(cache_key, query=question, client=client, top_k=4)
        if not results:
            return "No matching sections found in filing."

        output = []
        for i, res in enumerate(results, start=1):
            output.append(f"[Excerpt {i} | Similarity: {res['score']:.3f}]\n{res['chunk']}\n")
        return "\n".join(output)

    tools = [
        tool_cik_lookup,
        tool_full_text_search,
        tool_fetch_filing_text,
        tool_get_financial_facts,
        tool_query_filing_vector_database,
    ]

    system_instruction = (
        "You are an expert financial research agent with direct programmatic access to SEC EDGAR. "
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
