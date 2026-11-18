-- psql -v company_id=123 -v as_of=2025-12-31 -f db/research.sql
-- Parameters are a company node ID and a filing-date cutoff.
SELECT n.label AS auditor, count(*) AS companies
FROM (
    SELECT DISTINCT ON (company_id) company_id, auditor_id
    FROM sec.auditor_history(:'as_of'::date)
    ORDER BY company_id, filed_at DESC
) latest
JOIN sec.node n ON n.id = latest.auditor_id
GROUP BY n.id, n.label ORDER BY companies DESC, auditor;

SELECT c.ticker, old.label AS previous_auditor, new.label AS auditor, h.filed_at
FROM sec.auditor_history(:'as_of'::date) h
JOIN sec.node company ON company.id = h.company_id
JOIN sec.company c ON c.cik = company.cik
JOIN sec.node old ON old.id = h.previous_auditor_id
JOIN sec.node new ON new.id = h.auditor_id
WHERE h.auditor_id <> h.previous_auditor_id
ORDER BY h.filed_at DESC, c.ticker;

SELECT n.label, s.depth
FROM sec.subsidiaries(:'company_id'::bigint, :'as_of'::date) s
JOIN sec.node n ON n.id = s.node_id
ORDER BY s.depth, n.label;

-- Keep same-day conflicts visible and separate concepts, units and period lengths.
WITH series AS (
    SELECT t.*, dense_rank() OVER (
        PARTITION BY dimension_id, taxonomy, concept, unit, period_start, period_end
        ORDER BY filed_at DESC
    ) AS filing_rank
    FROM sec.reported_triple t
    WHERE subject_id = :'company_id'::bigint AND predicate = 'revenue_segment'
      AND source = 'xbrl' AND filed_at <= :'as_of'::date
)
SELECT n.label, s.taxonomy, s.concept, s.period_start, s.period_end,
       s.object_number, s.unit, s.accession, s.filed_at
FROM series s JOIN sec.node n ON n.id = s.dimension_id
WHERE s.filing_rank = 1
ORDER BY s.period_end DESC, n.label, s.unit, s.object_number DESC;
