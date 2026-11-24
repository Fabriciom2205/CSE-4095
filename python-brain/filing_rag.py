import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from bs4 import BeautifulSoup
from google import genai

import filing_store
import sec_client

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except ImportError:
    pass

DEFAULT_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
EMBEDDING_DIMENSIONS = 1536
# Increment when extraction or chunk construction changes.
CHUNK_VERSION = 1
MAX_CACHED_FILINGS = 20
log = logging.getLogger(__name__)

# In-memory store: {filing_key: {"chunks": list[str], "embeddings": np.ndarray}}
_filing_indices = {}

SECTION_RULES = {
    "business": (
        r"ITEM\s+1\.\s+BUSINESS\b",
        r"ITEM\s+(?:1A|1B|1C|2|3)\b",
    ),
    "risk_factors": (
        r"ITEM\s+1A\.\s+RISK\s+FACTORS\b",
        r"ITEM\s+(?:1B|1C|2|3|4|5|6|7)\b",
    ),
    "mda": (
        r"(?:ITEM\s+7\.\s+MANAGEMENT['’]S\s+DISCUSSION|ITEM\s+2\.\s+MANAGEMENT['’]S\s+DISCUSSION)\b",
        r"ITEM\s+(?:3|7A|7B|8)\b",
    ),
    "financials": (
        r"(?:ITEM\s+8\.\s+FINANCIAL\s+STATEMENTS|ITEM\s+1\.\s+FINANCIAL\s+STATEMENTS)\b",
        r"(?:ITEM\s+(?:2|9|9A|9B|10|11|12|13|14|15|16)\b|SIGNATURES|\Z)",
    ),
}


def _validate_section(section: str) -> str:
    target = section.lower().strip()
    if target not in (*SECTION_RULES, "key_sections", "all", "default"):
        raise ValueError("Unknown section; use business, risk_factors, mda, financials, or key_sections")
    return target


def _extract_longest_span(text: str, start_pat: str, end_pat: str) -> str:
    """Extracts the section body matching start/end patterns, skipping short TOC matches."""
    starts = [m.start() for m in re.finditer(r"^[ \t]*" + start_pat, text, re.IGNORECASE | re.MULTILINE)]
    ends = [m.start() for m in re.finditer(r"^[ \t]*" + end_pat + r"(?=\s*\.)", text, re.IGNORECASE | re.MULTILINE)]
    longest = ""
    for s in starts:
        valid_ends = [e for e in ends if e > s]
        if valid_ends:
            candidate = text[s:valid_ends[0]].strip()
            # TOC listings are typically < 300 chars between items; true body sections are much longer
            if len(candidate) > len(longest):
                longest = candidate
    return longest


def filter_filing_sections(text: str, section: str = "key_sections") -> str:
    """Extracts target filing sections (business, risk_factors, mda, financials), discarding exhibits and boilerplate."""
    target = _validate_section(section)

    if target in SECTION_RULES:
        start_pat, end_pat = SECTION_RULES[target]
        matched = _extract_longest_span(text, start_pat, end_pat)
        if matched:
            return matched

    if target in ("key_sections", "all", "default"):
        extracted = []
        for name, (start_pat, end_pat) in SECTION_RULES.items():
            content = _extract_longest_span(text, start_pat, end_pat)
            if content:
                extracted.append(content)
        if extracted:
            return "\n\n".join(extracted)

    # Fallback for non-standard filings: strip exhibits, legal disclosures, and signatures from tail
    text = re.sub(r"ITEM\s+3\.\s+LEGAL\s+PROCEEDINGS[\s\S]*?(?=ITEM\s+4\.)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"ITEM\s+15\.\s+EXHIBITS[\s\S]*", "", text, flags=re.IGNORECASE)
    # shortcut: regex section extraction without HTML anchor tag parsing, upgrade when multi-part amendment filings require strict XML anchor navigation
    return text


def clean_and_chunk_html(
    html_content: str,
    section: str = "key_sections",
    chunk_size: int = 1500,
    chunk_overlap: int = 250,
) -> list[str]:
    """Strips HTML boilerplate, isolates key sections, and yields semantic paragraph chunks without an arbitrary cap."""
    soup = BeautifulSoup(html_content, "html.parser")
    for elem in soup(["script", "style", "noscript", "header", "footer", "ix:header"]):
        elem.extract()
    for elem in soup.find_all(style=re.compile(r"display\s*:\s*none\b", re.IGNORECASE)):
        elem.extract()

    raw_text = soup.get_text(separator="\n")
    raw_text = re.sub(r"[ \t]+", " ", raw_text)

    # Filter for targeted high-value sections (Business, Risks, MD&A, Financials)
    body_text = filter_filing_sections(raw_text, section=section)
    paragraphs = [p.strip() for p in body_text.split("\n") if p.strip()]

    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        current_chunk.append(para)
        current_len += len(para)
        if current_len >= chunk_size:
            chunks.append(" ".join(current_chunk))
            # Preserve overlap for continuity
            overlap_len = 0
            overlap_paras = []
            for p in reversed(current_chunk):
                overlap_paras.insert(0, p)
                overlap_len += len(p)
                if overlap_len >= chunk_overlap:
                    break
            current_chunk = overlap_paras
            current_len = overlap_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def get_batch_embeddings(
    client: genai.Client,
    texts: list[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = 100,
) -> np.ndarray:
    """Embed each text separately; Gemini Embedding 2 aggregates multiple strings."""
    all_embeddings = []

    def embed(text):
        resp = client.models.embed_content(
            model=model, contents=text, config={"output_dimensionality": EMBEDDING_DIMENSIONS}
        )
        if not resp.embeddings or len(resp.embeddings) != 1:
            raise ValueError("Expected one embedding per text")
        vec = np.array(resp.embeddings[0].values, dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    with ThreadPoolExecutor(max_workers=4) as executor:
        for i in range(0, len(texts), batch_size):
            all_embeddings.extend(executor.map(embed, texts[i:i + batch_size]))

    return np.array(all_embeddings, dtype=np.float32)


def index_filing(
    key: str,
    chunks: list[str],
    client: genai.Client,
    model: str = DEFAULT_EMBEDDING_MODEL,
):
    """Embeds all filing chunks via batching and caches the normalized vector matrix in memory."""
    if key in _filing_indices or not chunks:
        return

    # FIFO cache eviction when exceeding maximum capacity
    if len(_filing_indices) >= MAX_CACHED_FILINGS:
        _filing_indices.pop(next(iter(_filing_indices)))

    embeddings = get_batch_embeddings(client, chunks, model=model, batch_size=100)
    _filing_indices[key] = {
        "chunks": chunks,
        "embeddings": embeddings,
    }


def query_filing_index(
    key: str,
    query: str,
    client: genai.Client,
    top_k: int = 5,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> list[dict]:
    """Runs cosine similarity search on the indexed filing matrix."""
    if key not in _filing_indices:
        return []

    index_data = _filing_indices[key]
    chunks = index_data["chunks"]
    matrix = index_data["embeddings"]

    q_vec = get_batch_embeddings(client, [query], model=model)[0]
    scores = np.dot(matrix, q_vec)

    top_indices = np.argsort(scores)[::-1][:top_k]
    return [{"chunk": chunks[i], "score": float(scores[i])} for i in top_indices]


def _postgres_embeddings(client, texts, model):
    try:
        embeddings = get_batch_embeddings(client, texts, model=model)
    except Exception as error:
        raise ValueError(f"Filing index embedding request failed ({type(error).__name__})") from None
    if (
        embeddings.shape != (len(texts), EMBEDDING_DIMENSIONS)
        or not np.isfinite(embeddings).all()
        or not np.any(embeddings, axis=1).all()
    ):
        raise ValueError(f"Filing index requires {EMBEDDING_DIMENSIONS}-dimensional, finite, nonzero embeddings")
    return embeddings


def _query_postgres(read_dsn, write_dsn, cik, accession, filename, section, question, client, top_k):
    model = DEFAULT_EMBEDDING_MODEL
    key = (cik, accession, filename, section, model, EMBEDDING_DIMENSIONS, CHUNK_VERSION)
    index_id = filing_store.find_index(read_dsn, key)
    if index_id is None:
        if not write_dsn:
            return []
        raw_html = sec_client.tool_fetch_filing_text(cik=cik, accession_number=accession, filename=filename)
        chunks = clean_and_chunk_html(raw_html, section=section)
        if not chunks:
            return None
        # shortcut: concurrent misses can repeat embedding work; coordinate builds if this becomes costly.
        embeddings = _postgres_embeddings(client, chunks, model)
        filing_store.publish_index(write_dsn, key, chunks, embeddings)
        index_id = filing_store.find_index(read_dsn, key)
        if index_id is None:
            raise filing_store.FilingStoreError("Published filing index is unavailable through SEC_RAG_READ_DSN")

    embedding = _postgres_embeddings(client, [question], model)[0]
    return filing_store.search_index(read_dsn, index_id, embedding, top_k)


def query_filing_rag(
    cik: str,
    accession_number: str,
    filename: str,
    question: str,
    client: genai.Client,
    section: str = "key_sections",
    top_k: int = 4,
) -> str:
    """Indexes targeted filing sections and runs vector similarity search with Gemini embeddings."""
    section = _validate_section(section)
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("Question must contain 1 to 2000 characters")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 10:
        raise ValueError("top_k must be between 1 and 10")
    cik = sec_client._validate_cik(cik)
    sec_client._validate_accession(accession_number)
    sec_client._validate_filename(filename)
    read_dsn = os.getenv("SEC_RAG_READ_DSN") or os.getenv("SEC_DB_READ_DSN")
    write_dsn = os.getenv("SEC_RAG_WRITE_DSN")
    if write_dsn and not read_dsn:
        raise ValueError("Configure SEC_RAG_READ_DSN or SEC_DB_READ_DSN to use PostgreSQL filing retrieval")
    results = []
    if read_dsn:
        try:
            results = _query_postgres(read_dsn, write_dsn, cik, accession_number, filename, section, question, client, top_k)
        except filing_store.FilingStoreError as error:
            log.warning("%s; using in-memory filing retrieval", error)
    if results is None:
        return "No matching content found in target filing section."
    if not results:
        cache_key = f"{cik}_{accession_number}_{filename}_{section}"
        if cache_key not in _filing_indices:
            raw_html = sec_client.tool_fetch_filing_text(cik=cik, accession_number=accession_number, filename=filename)
            chunks = clean_and_chunk_html(raw_html, section=section)
            if not chunks:
                return "No matching content found in target filing section."
            index_filing(cache_key, chunks, client=client)
        results = query_filing_index(cache_key, query=question, client=client, top_k=top_k)
    if not results:
        return "No matching sections found in filing."

    output = [f"[Excerpt {i} | Similarity: {res['score']:.3f}]\n{res['chunk']}\n" for i, res in enumerate(results, start=1)]
    return "\n".join(output)
