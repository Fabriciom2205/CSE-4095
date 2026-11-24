BEGIN;

ALTER TABLE portfolio.risk_limit
    ADD COLUMN max_daily_orders integer CHECK (max_daily_orders > 0),
    ADD COLUMN max_daily_notional numeric CHECK (max_daily_notional > 0 AND max_daily_notional < 'Infinity');

CREATE TABLE portfolio.equity_snapshot (
    account_id bigint NOT NULL REFERENCES portfolio.account,
    observed_at timestamptz NOT NULL,
    equity numeric NOT NULL CHECK (equity > 0 AND equity < 'Infinity'),
    PRIMARY KEY (account_id, observed_at)
);

-- Immutable decision payload and broker lifecycle for each write-ahead order.
CREATE TABLE portfolio.decision (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    digest text NOT NULL UNIQUE CHECK (digest ~ '^[0-9a-f]{64}$'),
    account_id bigint NOT NULL REFERENCES portfolio.account,
    symbol text NOT NULL CHECK (symbol ~ '^[A-Z][A-Z0-9.-]{0,9}$'),
    side text NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity bigint NOT NULL CHECK (quantity > 0),
    limit_price numeric NOT NULL CHECK (limit_price > 0 AND limit_price < 'Infinity'),
    client_order_id text NOT NULL UNIQUE CHECK (client_order_id = 'monroe-' || left(digest, 32)),
    state text NOT NULL CHECK (state IN ('intent', 'submitted', 'rejected', 'unknown')),
    proposal jsonb NOT NULL,
    risk_inputs jsonb NOT NULL,
    broker_order_id text,
    broker_status text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    settled_at timestamptz
);

-- Several authorizations may resolve to the same decision. Persist each retry key.
CREATE TABLE portfolio.order_intent (
    decision_key text PRIMARY KEY CHECK (decision_key ~ '^[A-Za-z0-9_-]{1,80}$'),
    request_digest text NOT NULL CHECK (request_digest ~ '^[0-9a-f]{64}$'),
    decision_id bigint NOT NULL REFERENCES portfolio.decision
);

CREATE INDEX decision_account_created ON portfolio.decision (account_id, created_at);

COMMIT;
