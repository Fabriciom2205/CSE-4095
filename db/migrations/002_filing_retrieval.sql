BEGIN;

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

CREATE TABLE sec.filing_retrieval_index (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cik text NOT NULL CHECK (cik ~ '^[0-9]{10}$' AND cik <> '0000000000'),
    accession text NOT NULL CHECK (accession ~ '^[0-9]{10}-[0-9]{2}-[0-9]{6}$'),
    filename text NOT NULL,
    section text NOT NULL,
    embedding_model text NOT NULL,
    embedding_dimensions integer NOT NULL CHECK (embedding_dimensions = 1536),
    chunk_version integer NOT NULL CHECK (chunk_version > 0),
    UNIQUE (cik, accession, filename, section, embedding_model, embedding_dimensions, chunk_version)
);

CREATE TABLE sec.filing_retrieval_chunk (
    index_id bigint NOT NULL REFERENCES sec.filing_retrieval_index ON DELETE CASCADE,
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    content text NOT NULL CHECK (length(btrim(content)) > 0),
    embedding public.vector(1536) NOT NULL,
    PRIMARY KEY (index_id, ordinal)
);

COMMIT;
