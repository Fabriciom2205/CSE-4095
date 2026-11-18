BEGIN;

CREATE SCHEMA sec;

CREATE TABLE sec.company (
    cik text PRIMARY KEY CHECK (cik ~ '^[0-9]{10}$' AND cik <> '0000000000'),
    ticker text NOT NULL,
    name text NOT NULL
);

CREATE TABLE sec.filing (
    accession text PRIMARY KEY CHECK (accession ~ '^[0-9]{10}-[0-9]{2}-[0-9]{6}$'),
    cik text NOT NULL REFERENCES sec.company,
    form text NOT NULL,
    filed_at date NOT NULL,
    UNIQUE (accession, filed_at)
);

CREATE TABLE sec.fact (
    accession text NOT NULL REFERENCES sec.filing,
    taxonomy text NOT NULL,
    concept text NOT NULL,
    unit text NOT NULL,
    period_start date,
    period_end date NOT NULL,
    value numeric NOT NULL CHECK (value NOT IN ('NaN', 'Infinity', '-Infinity')),
    CHECK (period_start <= period_end),
    UNIQUE NULLS NOT DISTINCT (accession, taxonomy, concept, unit, period_start, period_end, value)
);

CREATE TABLE sec.chunk (
    id bigint GENERATED ALWAYS AS IDENTITY,
    accession text NOT NULL REFERENCES sec.filing,
    content text NOT NULL CHECK (length(btrim(content)) > 0),
    PRIMARY KEY (accession, id)
);

CREATE TABLE sec.node (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('company', 'person', 'auditor', 'dimension', 'counterparty')),
    key text NOT NULL CHECK (length(btrim(key)) > 0),
    label text NOT NULL,
    cik text REFERENCES sec.company,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (kind, key),
    CHECK (cik IS NULL OR (kind = 'company' AND key = cik))
);

CREATE TABLE sec.triple (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject_id bigint NOT NULL REFERENCES sec.node,
    predicate text NOT NULL,
    object_node_id bigint REFERENCES sec.node,
    object_text text,
    object_number numeric CHECK (object_number NOT IN ('NaN', 'Infinity', '-Infinity')),
    dimension_id bigint REFERENCES sec.node,
    taxonomy text,
    concept text,
    unit text,
    period_start date,
    period_end date,
    filed_at date NOT NULL,
    accession text NOT NULL,
    source text NOT NULL CHECK (source IN ('xbrl', 'exhibit21', 'def14a', 'form4', 'llm_extracted')),
    confidence numeric,
    chunk_id bigint,
    FOREIGN KEY (accession, filed_at) REFERENCES sec.filing (accession, filed_at),
    FOREIGN KEY (accession, chunk_id) REFERENCES sec.chunk (accession, id),
    CHECK (num_nonnulls(object_node_id, object_text, object_number) = 1),
    CHECK (period_start IS NULL OR (period_end IS NOT NULL AND period_start <= period_end)),
    CHECK (
        (predicate IN ('has_subsidiary', 'audited_by', 'officer_of', 'director_of',
                       'insider_of', 'party_to', 'major_customer_of')
         AND object_node_id IS NOT NULL
         AND num_nonnulls(dimension_id, taxonomy, concept, unit, period_start, period_end) = 0)
        OR
        (predicate IN ('revenue_segment', 'revenue_geography', 'operating_income_segment',
                       'assets_segment', 'long_lived_assets_geography', 'reports_metric')
         AND object_number IS NOT NULL AND dimension_id IS NOT NULL AND taxonomy IS NOT NULL
         AND concept IS NOT NULL AND unit IS NOT NULL AND period_end IS NOT NULL AND source = 'xbrl')
    ),
    CHECK (
        (source = 'llm_extracted' AND confidence IS NOT NULL AND confidence BETWEEN 0 AND 1
         AND chunk_id IS NOT NULL)
        OR (source <> 'llm_extracted' AND confidence IS NULL AND chunk_id IS NULL)
    ),
    UNIQUE NULLS NOT DISTINCT (accession, subject_id, predicate, object_node_id, object_text,
                               object_number, dimension_id, taxonomy, concept, unit,
                               period_start, period_end, source, chunk_id)
);

CREATE INDEX filing_company_date ON sec.filing (cik, filed_at DESC);
CREATE INDEX triple_subject_pred ON sec.triple (subject_id, predicate, period_end DESC);
CREATE INDEX triple_reverse ON sec.triple (predicate, object_node_id) WHERE object_node_id IS NOT NULL;

-- Model-extracted assertions require a separate review workflow.
CREATE VIEW sec.reported_triple AS
SELECT * FROM sec.triple WHERE source <> 'llm_extracted';

-- Compare distinct filing-day observations. An ambiguous day breaks the comparison.
CREATE FUNCTION sec.auditor_history(as_of date)
RETURNS TABLE (company_id bigint, auditor_id bigint, previous_auditor_id bigint, filed_at date)
LANGUAGE sql STABLE AS $$
    WITH observations AS (
        SELECT t.subject_id, t.filed_at,
               CASE WHEN count(DISTINCT t.object_node_id) = 1 THEN min(t.object_node_id) END AS auditor
        FROM sec.reported_triple t
        JOIN sec.filing f ON f.accession = t.accession
        JOIN sec.node company ON company.id = t.subject_id AND company.cik = f.cik
        JOIN sec.node auditor ON auditor.id = t.object_node_id AND auditor.kind = 'auditor'
        WHERE t.predicate = 'audited_by' AND t.source = 'xbrl' AND t.filed_at <= as_of
        GROUP BY t.subject_id, t.filed_at
    )
    SELECT subject_id, auditor, lag(auditor) OVER company_history, observations.filed_at
    FROM observations
    WINDOW company_history AS (PARTITION BY subject_id ORDER BY observations.filed_at);
$$;

-- Positive assertions seen by the cutoff do not establish current ownership.
CREATE FUNCTION sec.subsidiaries(parent_id bigint, as_of date)
RETURNS TABLE (node_id bigint, depth integer)
LANGUAGE sql STABLE AS $$
    WITH RECURSIVE edges AS NOT MATERIALIZED (
        SELECT DISTINCT subject_id, object_node_id
        FROM sec.reported_triple
        WHERE predicate = 'has_subsidiary' AND source = 'exhibit21' AND filed_at <= as_of
    ), tree(id, depth, path) AS (
        SELECT parent_id, 0, ARRAY[parent_id]
        UNION ALL
        SELECT e.object_node_id, t.depth + 1, t.path || e.object_node_id
        FROM tree t JOIN edges e ON e.subject_id = t.id
        WHERE t.depth < 10 AND e.object_node_id <> ALL (t.path)
    )
    SELECT id, min(t.depth) FROM tree t WHERE t.depth > 0 GROUP BY id;
$$;

COMMIT;
