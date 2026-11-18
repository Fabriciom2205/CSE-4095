-- Called inside the ingestion transaction after copying the batch into a temporary table.
INSERT INTO sec.company (cik, ticker, name)
SELECT c.cik, c.ticker, c.name
FROM sec_batch b CROSS JOIN LATERAL jsonb_to_record(b.payload->'company') AS c(cik text, ticker text, name text)
ON CONFLICT (cik) DO UPDATE SET ticker = excluded.ticker, name = excluded.name;

INSERT INTO sec.filing (accession, cik, form, filed_at)
SELECT DISTINCT f.accession, f.cik, f.form, f.filed_at
FROM sec_batch b CROSS JOIN LATERAL jsonb_to_recordset(b.payload->'filings')
    AS f(accession text, cik text, form text, filed_at date)
ON CONFLICT (accession) DO NOTHING;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM sec_batch b CROSS JOIN LATERAL jsonb_to_recordset(b.payload->'filings')
            AS f(accession text, cik text, form text, filed_at date)
        JOIN sec.filing existing USING (accession)
        WHERE (f.cik, f.form, f.filed_at) <> (existing.cik, existing.form, existing.filed_at)
    ) THEN
        RAISE EXCEPTION 'Conflicting SEC filing provenance';
    END IF;
END
$$;

INSERT INTO sec.fact (accession, taxonomy, concept, unit, period_start, period_end, value)
SELECT f.accession, f.taxonomy, f.concept, f.unit, f.period_start, f.period_end, f.value
FROM sec_batch b CROSS JOIN LATERAL jsonb_to_recordset(b.payload->'facts')
    AS f(accession text, taxonomy text, concept text, unit text, period_start date, period_end date, value numeric)
ON CONFLICT DO NOTHING;

INSERT INTO sec.node (kind, key, label, cik)
SELECT 'company', c.cik, c.name, c.cik
FROM sec_batch b CROSS JOIN LATERAL jsonb_to_record(b.payload->'company') AS c(cik text, name text)
WHERE jsonb_array_length(b.payload->'auditors') > 0
ON CONFLICT (kind, key) DO UPDATE SET label = excluded.label, cik = excluded.cik;

INSERT INTO sec.node (kind, key, label)
SELECT 'auditor', a.key, a.label
FROM sec_batch b CROSS JOIN LATERAL jsonb_to_recordset(b.payload->'auditors') AS a(key text, label text)
ON CONFLICT (kind, key) DO NOTHING;

INSERT INTO sec.triple (subject_id, predicate, object_node_id, filed_at, accession, source)
SELECT company.id, 'audited_by', auditor.id, f.filed_at, f.accession, 'xbrl'
FROM sec_batch b CROSS JOIN LATERAL jsonb_to_recordset(b.payload->'auditors') AS a(accession text, key text)
JOIN sec.filing f USING (accession)
JOIN sec.node company ON company.kind = 'company' AND company.cik = f.cik
JOIN sec.node auditor ON auditor.kind = 'auditor' AND auditor.key = a.key
ON CONFLICT DO NOTHING;
