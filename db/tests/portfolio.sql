-- Apply migration 003, then run: psql -X -v ON_ERROR_STOP=1 -f db/tests/portfolio.sql
BEGIN;

DO $$
DECLARE
    account_pk bigint;
BEGIN
    INSERT INTO portfolio.account (provider, environment, external_account_id, status, currency,
                                   equity, cash, buying_power, observed_at)
    VALUES ('alpaca', 'paper', 'test-account', 'ACTIVE', 'USD', 950, 1000, 900, now())
    RETURNING id INTO account_pk;

    INSERT INTO portfolio.position (account_id, asset_id, asset_class, symbol, side, quantity,
                                    market_value, cost_basis, unrealized_pl, observed_at)
    VALUES (account_pk, 'asset', 'us_equity', 'AAA', 'short', -0.25, -50, -40, -10, now());

    INSERT INTO portfolio.trade (account_id, external_trade_id, external_order_id, symbol, side,
                                 quantity, price, executed_at)
    VALUES (account_pk, 'fill-1', 'shared-order', 'AAA', 'sell', 0.10, 161, now()),
           (account_pk, 'fill-2', 'shared-order', 'AAA', 'sell', 0.15, 159, now());

    INSERT INTO portfolio.risk_limit (account_id, max_name_weight, max_drawdown, max_order_notional)
    VALUES (account_pk, 0.25, 0.10, 100);

    BEGIN
        UPDATE portfolio.position SET market_value = 50 WHERE account_id = account_pk;
        RAISE EXCEPTION 'Short position accepted a positive signed market value';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        UPDATE portfolio.risk_limit SET max_drawdown = 1.01 WHERE account_id = account_pk;
        RAISE EXCEPTION 'Drawdown above 100%% was accepted as a fraction';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        UPDATE portfolio.risk_limit SET max_order_notional = 'Infinity' WHERE account_id = account_pk;
        RAISE EXCEPTION 'Nonfinite notional was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        DELETE FROM portfolio.account WHERE id = account_pk;
        RAISE EXCEPTION 'An account with trade history was droppable';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;
END
$$;

ROLLBACK;
