BEGIN;

ALTER TABLE outbox
    ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0;
ALTER TABLE outbox
    ADD COLUMN IF NOT EXISTS last_attempt_at timestamptz;
ALTER TABLE outbox
    ADD COLUMN IF NOT EXISTS next_attempt_at timestamptz;
ALTER TABLE outbox
    ADD COLUMN IF NOT EXISTS last_error varchar(500);
ALTER TABLE outbox
    ADD COLUMN IF NOT EXISTS dead_lettered_at timestamptz;

CREATE INDEX IF NOT EXISTS ix_outbox_delivery_ready
    ON outbox (next_attempt_at, created_at)
    WHERE sent_at IS NULL AND dead_lettered_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_outbox_dead_lettered
    ON outbox (dead_lettered_at)
    WHERE dead_lettered_at IS NOT NULL AND sent_at IS NULL;

INSERT INTO schema_migrations(version)
VALUES ('0003_outbox_delivery')
ON CONFLICT (version) DO NOTHING;

COMMIT;
