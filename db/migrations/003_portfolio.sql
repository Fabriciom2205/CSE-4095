BEGIN;

CREATE SCHEMA portfolio;

CREATE TABLE portfolio.account (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider text NOT NULL CHECK (btrim(provider) <> ''),
    environment text NOT NULL CHECK (environment IN ('paper', 'live')),
    external_account_id text NOT NULL CHECK (btrim(external_account_id) <> ''),
    status text NOT NULL CHECK (btrim(status) <> ''),
    currency text CHECK (currency ~ '^[A-Z]{3}$'),
    equity numeric CHECK (equity NOT IN ('NaN', 'Infinity', '-Infinity')),
    cash numeric CHECK (cash NOT IN ('NaN', 'Infinity', '-Infinity')),
    buying_power numeric CHECK (buying_power NOT IN ('NaN', 'Infinity', '-Infinity')),
    observed_at timestamptz NOT NULL,
    UNIQUE (provider, environment, external_account_id)
);

CREATE TABLE portfolio.position (
    account_id bigint NOT NULL REFERENCES portfolio.account ON DELETE CASCADE,
    asset_id text NOT NULL CHECK (btrim(asset_id) <> ''),
    asset_class text NOT NULL CHECK (btrim(asset_class) <> ''),
    symbol text NOT NULL CHECK (btrim(symbol) <> ''),
    side text NOT NULL CHECK (side IN ('long', 'short')),
    quantity numeric NOT NULL CHECK (quantity <> 0 AND quantity NOT IN ('NaN', 'Infinity', '-Infinity')),
    market_value numeric CHECK (market_value NOT IN ('NaN', 'Infinity', '-Infinity')),
    cost_basis numeric NOT NULL CHECK (cost_basis NOT IN ('NaN', 'Infinity', '-Infinity')),
    unrealized_pl numeric CHECK (unrealized_pl NOT IN ('NaN', 'Infinity', '-Infinity')),
    observed_at timestamptz NOT NULL,
    CHECK ((side = 'long' AND quantity > 0 AND (market_value IS NULL OR market_value >= 0))
        OR (side = 'short' AND quantity < 0 AND (market_value IS NULL OR market_value <= 0))),
    PRIMARY KEY (account_id, asset_id)
);

-- Each row represents an execution fill. An order can have multiple independent fills.
CREATE TABLE portfolio.trade (
    account_id bigint NOT NULL REFERENCES portfolio.account,
    external_trade_id text NOT NULL CHECK (btrim(external_trade_id) <> ''),
    external_order_id text CHECK (btrim(external_order_id) <> ''),
    symbol text NOT NULL CHECK (btrim(symbol) <> ''),
    side text NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity numeric NOT NULL CHECK (quantity > 0 AND quantity < 'Infinity'),
    price numeric NOT NULL CHECK (price > 0 AND price < 'Infinity'),
    executed_at timestamptz NOT NULL,
    PRIMARY KEY (account_id, external_trade_id)
);

CREATE INDEX trade_account_executed_at ON portfolio.trade (account_id, executed_at DESC);

-- NULL disables the corresponding cap. Weights and drawdown use fractions of equity.
CREATE TABLE portfolio.risk_limit (
    account_id bigint PRIMARY KEY REFERENCES portfolio.account ON DELETE CASCADE,
    max_name_weight numeric CHECK (max_name_weight BETWEEN 0 AND 1),
    max_sector_weight numeric CHECK (max_sector_weight BETWEEN 0 AND 1),
    max_order_notional numeric CHECK (max_order_notional >= 0 AND max_order_notional < 'Infinity'),
    max_gross_notional numeric CHECK (max_gross_notional >= 0 AND max_gross_notional < 'Infinity'),
    max_drawdown numeric CHECK (max_drawdown BETWEEN 0 AND 1)
);

COMMIT;
