BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
    id varchar(36) PRIMARY KEY,
    broker_order_id varchar(128),
    client_order_id varchar(128) UNIQUE,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_orders_broker_order_id ON orders (broker_order_id);
CREATE INDEX IF NOT EXISTS ix_orders_client_order_id ON orders (client_order_id);

CREATE TABLE IF NOT EXISTS quotes (
    symbol varchar(32) PRIMARY KEY,
    payload jsonb NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS signals (
    id varchar(36) PRIMARY KEY,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id varchar(36) PRIMARY KEY,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id varchar(36) PRIMARY KEY,
    payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency_keys (
    client_order_id varchar(128) PRIMARY KEY,
    created_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
    id varchar(36) PRIMARY KEY,
    topic varchar(128) NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    sent_at timestamptz
);
CREATE TABLE IF NOT EXISTS runtime_state (
    key varchar(128) PRIMARY KEY,
    payload jsonb NOT NULL,
    updated_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS live_approvals (
    id varchar(36) PRIMARY KEY,
    fingerprint varchar(64) NOT NULL,
    intent jsonb NOT NULL,
    created_by varchar(128) NOT NULL,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    consumed_by varchar(128)
);
CREATE INDEX IF NOT EXISTS ix_live_approvals_fingerprint
    ON live_approvals (fingerprint);

INSERT INTO schema_migrations(version)
VALUES ('0001_core')
ON CONFLICT (version) DO NOTHING;

COMMIT;
