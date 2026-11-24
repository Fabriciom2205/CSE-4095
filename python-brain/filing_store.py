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
        raise FilingStoreError(f"PostgreSQL {operation} failed ({reason})") from None


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


def query_facts(dsn, cik, selectors, *, first_end=None, last_end=None, instant=None):
    """Read the latest filing for each matching XBRL context, preserving same-day conflicts."""
    taxonomies, concepts, units = map(list, zip(*selectors, strict=True))
    with _connect(dsn, "fact lookup") as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        return conn.execute(
            """
            WITH ranked AS (
                SELECT x.taxonomy, x.concept, x.unit, x.period_start, x.period_end,
                       x.value, f.accession, f.filed_at, f.form,
                       bool_or(f.form IN ('10-Q', '10-Q/A')) OVER context AS has_quarterly_filing,
                       dense_rank() OVER (
                           PARTITION BY x.taxonomy, x.concept, x.unit, x.period_start, x.period_end
                           ORDER BY f.filed_at DESC
                       ) AS filing_rank
                FROM sec.fact x
                JOIN sec.filing f USING (accession)
                JOIN unnest(%s::text[], %s::text[], %s::text[]) AS wanted(taxonomy, concept, unit)
                  ON x.taxonomy = wanted.taxonomy AND x.concept = wanted.concept
                 AND (wanted.unit IS NULL OR x.unit = wanted.unit)
                WHERE f.cik = %s
                  AND x.period_end BETWEEN coalesce(%s::date, '-infinity') AND coalesce(%s::date, 'infinity')
                  AND (%s::boolean IS NULL OR (x.period_start IS NULL) = %s)
                WINDOW context AS (PARTITION BY x.taxonomy, x.concept, x.unit, x.period_start, x.period_end)
            )
            SELECT taxonomy, concept, unit, period_start, period_end, value, accession, filed_at, form,
                   has_quarterly_filing
            FROM ranked WHERE filing_rank = 1
            ORDER BY period_end DESC, filed_at DESC, accession DESC, period_start DESC, value
            """,
            (taxonomies, concepts, units, cik, first_end, last_end, instant, instant),
        ).fetchall()


def query_relations(dsn, cik, predicate, as_of):
    with _connect(dsn, "relationship lookup") as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        return conn.execute(
            """
            SELECT t.predicate, obj.label, obj.kind, obj.cik, dim.label, t.taxonomy, t.concept,
                   t.object_number, t.unit, t.period_start, t.period_end, t.accession, t.filed_at, t.source
            FROM sec.reported_triple t
            JOIN sec.node subject ON subject.id = t.subject_id
            JOIN sec.filing f ON f.accession = t.accession AND f.cik = subject.cik
            LEFT JOIN sec.node obj ON obj.id = t.object_node_id
            LEFT JOIN sec.node dim ON dim.id = t.dimension_id
            WHERE subject.cik = %s AND t.predicate = %s AND t.filed_at <= %s
            ORDER BY t.filed_at DESC, t.id DESC
            LIMIT 51
            """,
            (cik, predicate, as_of),
        ).fetchall()
