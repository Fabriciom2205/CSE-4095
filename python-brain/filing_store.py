"""Read and publish versioned SEC filing indexes in PostgreSQL."""

from contextlib import contextmanager

import psycopg


class FilingStoreError(Exception):
    """A safe database error that can be returned by a research tool."""


@contextmanager
def _connect(dsn, operation):
    try:
        with psycopg.connect(dsn, connect_timeout=5) as conn:
            conn.execute("SET LOCAL statement_timeout = '30s'")
            yield conn
    except psycopg.Error as error:
        reason = error.sqlstate or type(error).__name__
        raise FilingStoreError(f"PostgreSQL filing index {operation} failed ({reason})") from None


def find_index(dsn, key):
    with _connect(dsn, "lookup") as conn:
        row = conn.execute(
            """
            SELECT id FROM sec.filing_retrieval_index
            WHERE (cik, accession, filename, section, embedding_model, embedding_dimensions, chunk_version)
                = (%s, %s, %s, %s, %s, %s, %s)
            """,
            key,
        ).fetchone()
    return row[0] if row else None


def publish_index(dsn, key, chunks, embeddings):
    # The index and its chunks become visible together when this transaction commits.
    with _connect(dsn, "publish") as conn:
        row = conn.execute(
            """
            INSERT INTO sec.filing_retrieval_index
                (cik, accession, filename, section, embedding_model, embedding_dimensions, chunk_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            key,
        ).fetchone()
        if row is None:
            return
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO sec.filing_retrieval_chunk (index_id, ordinal, content, embedding)
                VALUES (%s, %s, %s, %s::real[]::public.vector)
                """,
                (
                    (row[0], ordinal, chunk, embedding.tolist())
                    for ordinal, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
                ),
            )


def search_index(dsn, index_id, embedding, top_k):
    with _connect(dsn, "search") as conn:
        rows = conn.execute(
            """
            SELECT content, 1 - (embedding OPERATOR(public.<=>) %s::real[]::public.vector) AS score
            FROM sec.filing_retrieval_chunk
            WHERE index_id = %s
            ORDER BY score DESC, ordinal
            LIMIT %s
            """,
            (embedding.tolist(), index_id, top_k),
        ).fetchall()
    return [{"chunk": chunk, "score": score} for chunk, score in rows]
