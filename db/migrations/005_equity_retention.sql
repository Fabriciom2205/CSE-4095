BEGIN;

-- Keep detailed equity observations for 90 days and one older high-water mark per account.
-- Use the oldest occurrence of an equal peak to preserve its original observation date.
CREATE FUNCTION portfolio.prune_equity_snapshots() RETURNS bigint
LANGUAGE sql
SET search_path = pg_catalog, pg_temp
AS $$
    WITH ranked AS (
        SELECT account_id, observed_at,
               row_number() OVER (PARTITION BY account_id ORDER BY equity DESC, observed_at) AS rank
        FROM portfolio.equity_snapshot
        WHERE observed_at < statement_timestamp() - interval '90 days'
    ), deleted AS (
        DELETE FROM portfolio.equity_snapshot AS snapshot
        USING ranked
        WHERE ranked.rank > 1 AND snapshot.account_id = ranked.account_id
          AND snapshot.observed_at = ranked.observed_at
        RETURNING 1
    )
    SELECT count(*) FROM deleted;
$$;

REVOKE ALL ON FUNCTION portfolio.prune_equity_snapshots() FROM PUBLIC;

COMMIT;
