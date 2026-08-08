BEGIN;

CREATE TABLE IF NOT EXISTS order_events (
    id varchar(36) PRIMARY KEY,
    order_id varchar(36) NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_order_events_order_id ON order_events (order_id);

CREATE TABLE IF NOT EXISTS fills (
    id varchar(36) PRIMARY KEY,
    broker_fill_id varchar(128) UNIQUE,
    order_id varchar(36),
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fills_broker_fill_id ON fills (broker_fill_id);
CREATE INDEX IF NOT EXISTS ix_fills_order_id ON fills (order_id);

CREATE TABLE IF NOT EXISTS risk_evaluations (
    id varchar(36) PRIMARY KEY,
    client_order_id varchar(128),
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_risk_evaluations_client_order_id
    ON risk_evaluations (client_order_id);

CREATE TABLE IF NOT EXISTS account_snapshots (
    id varchar(36) PRIMARY KEY,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_versions (
    id varchar(36) PRIMARY KEY,
    name varchar(64) NOT NULL,
    version varchar(64) NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    UNIQUE (name, version)
);
CREATE INDEX IF NOT EXISTS ix_strategy_versions_name ON strategy_versions (name);

CREATE TABLE IF NOT EXISTS strategy_runs (
    id varchar(36) PRIMARY KEY,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS market_bars (
    bar_key varchar(160) PRIMARY KEY,
    symbol varchar(32) NOT NULL,
    timeframe varchar(16) NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_market_bars_symbol ON market_bars (symbol);
CREATE INDEX IF NOT EXISTS ix_market_bars_timeframe ON market_bars (timeframe);
CREATE INDEX IF NOT EXISTS ix_market_bars_symbol_timeframe_time
    ON market_bars (symbol, timeframe, created_at);

INSERT INTO schema_migrations(version)
VALUES ('0002_priority_state')
ON CONFLICT (version) DO NOTHING;

COMMIT;
