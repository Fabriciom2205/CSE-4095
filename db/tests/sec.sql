-- psql -X -v ON_ERROR_STOP=1 -f db/tests/sec.sql (after applying the migration)
BEGIN;

INSERT INTO sec.company VALUES ('0000000001','ONE','One');
INSERT INTO sec.filing VALUES
    ('0000000001-24-000001','0000000001','10-K','2024-02-01'),
    ('0000000001-25-000001','0000000001','10-K','2025-02-01');
INSERT INTO sec.chunk (accession, content)
VALUES ('0000000001-24-000001', 'Evidence');
INSERT INTO sec.node (kind, key, label, cik) VALUES ('company','0000000001','One','0000000001');
INSERT INTO sec.node (kind, key, label) VALUES
    ('auditor','a','A'), ('auditor','b','B'), ('company','sub','Subsidiary'),
    ('dimension','0000000001:segment:retail','Retail');

DO $$
DECLARE
    root bigint := (SELECT id FROM sec.node WHERE key = '0000000001');
    a bigint := (SELECT id FROM sec.node WHERE key = 'a');
    b bigint := (SELECT id FROM sec.node WHERE key = 'b');
    sub bigint := (SELECT id FROM sec.node WHERE key = 'sub');
    segment bigint := (SELECT id FROM sec.node WHERE kind = 'dimension');
    evidence bigint := (SELECT id FROM sec.chunk WHERE accession = '0000000001-24-000001');
BEGIN
    INSERT INTO sec.triple (subject_id,predicate,object_node_id,filed_at,accession,source)
    VALUES (root,'audited_by',a,'2024-02-01','0000000001-24-000001','xbrl'),
           (root,'audited_by',b,'2025-02-01','0000000001-25-000001','xbrl'),
           (root,'has_subsidiary',root,'2024-02-01','0000000001-24-000001','exhibit21'),
           (root,'has_subsidiary',sub,'2024-02-01','0000000001-24-000001','exhibit21'),
           (root,'has_subsidiary',sub,'2025-02-01','0000000001-25-000001','exhibit21'),
           (sub,'has_subsidiary',root,'2025-02-01','0000000001-25-000001','exhibit21');

    INSERT INTO sec.triple (subject_id,predicate,object_number,dimension_id,taxonomy,concept,unit,
                            period_end,filed_at,accession,source)
    VALUES (root,'revenue_segment',4.5,segment,'us-gaap','Revenue','USD','2023-12-31',
            '2024-02-01','0000000001-24-000001','xbrl');

    INSERT INTO sec.triple (subject_id,predicate,object_node_id,filed_at,accession,source,confidence,chunk_id)
    VALUES (root,'audited_by',b,'2024-02-01','0000000001-24-000001','llm_extracted',0.8,evidence);

    IF NOT EXISTS (SELECT FROM sec.auditor_history('2024-12-31') h WHERE h.auditor_id = a)
        OR NOT EXISTS (SELECT FROM sec.auditor_history('2025-02-01') h
                       WHERE h.auditor_id = b AND h.previous_auditor_id = a)
        OR (SELECT array_agg(s.node_id) FROM sec.subsidiaries(root,'2025-02-01') s)
           IS DISTINCT FROM ARRAY[sub]
        OR EXISTS (SELECT FROM sec.reported_triple WHERE source = 'llm_extracted') THEN
        RAISE EXCEPTION 'Unexpected graph results';
    END IF;

    BEGIN
        INSERT INTO sec.triple (subject_id,predicate,object_node_id,filed_at,accession,source,confidence,chunk_id)
        VALUES (root,'audited_by',a,'2025-02-01','0000000001-25-000001','llm_extracted',0.8,evidence);
        RAISE EXCEPTION 'Cross-filing evidence was accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO sec.triple (subject_id,predicate,object_node_id,object_number,filed_at,accession,source)
        VALUES (root,'audited_by',a,1,'2025-02-01','0000000001-25-000001','xbrl');
        RAISE EXCEPTION 'Two edge objects were accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    INSERT INTO sec.triple (subject_id,predicate,object_node_id,filed_at,accession,source)
    VALUES (root,'audited_by',a,'2025-02-01','0000000001-25-000001','xbrl');

    IF NOT EXISTS (SELECT FROM sec.auditor_history('2025-02-01') h
                   WHERE h.filed_at = '2025-02-01' AND h.auditor_id IS NULL) THEN
        RAISE EXCEPTION 'Ambiguous auditor reporting must remain unresolved';
    END IF;
END
$$;

ROLLBACK;
