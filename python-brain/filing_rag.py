import os
import re
import numpy as np
from bs4 import BeautifulSoup
from google import genai

DEFAULT_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
FALLBACK_EMBEDDING_MODEL = "text-embedding-004"

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


def _extract_longest_span(text: str, start_pat: str, end_pat: str) -> str:
    """Extracts the section body matching start/end patterns, skipping short TOC matches."""
    starts = [m.start() for m in re.finditer(start_pat, text, re.IGNORECASE)]
    ends = [m.start() for m in re.finditer(end_pat, text, re.IGNORECASE)]
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
    target = section.lower().strip()

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
    for elem in soup(["script", "style", "noscript", "header", "footer"]):
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
    """Embeds a list of texts in batches of up to 100 per HTTP request with automatic fallback."""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            resp = client.models.embed_content(model=model, contents=batch)
        except Exception:
            # Fallback to secondary model if primary model is unavailable or lacks permission
            resp = client.models.embed_content(model=FALLBACK_EMBEDDING_MODEL, contents=batch)

        # Handle batch or single result payload
        if hasattr(resp, "embeddings") and resp.embeddings:
            for item in resp.embeddings:
                vec = np.array(item.values, dtype=np.float32)
                norm = np.linalg.norm(vec)
                all_embeddings.append(vec / norm if norm > 0 else vec)
        elif hasattr(resp, "embedding") and resp.embedding:
            vec = np.array(resp.embedding.values, dtype=np.float32)
            norm = np.linalg.norm(vec)
            all_embeddings.append(vec / norm if norm > 0 else vec)

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
