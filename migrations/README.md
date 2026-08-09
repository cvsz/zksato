# Database migrations

The managed PostgreSQL migration chain is:

- `0001_core.sql` — baseline orders, audit, idempotency, outbox, approvals, and runtime state.
- `0002_priority_state.sql` — durable operational evidence, research state, fills, and bars.
- `0003_outbox_delivery.sql` — durable webhook attempt/retry/dead-letter delivery state.

The application also calls SQLAlchemy `metadata.create_all()` as a safe local/bootstrap mechanism for new local databases, but production deployments must apply versioned SQL migrations explicitly before starting a new application release.

Example:

```bash
set -euo pipefail
for migration in migrations/[0-9][0-9][0-9][0-9]_*.sql; do
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration"
done
```

Rules:

- Apply migrations strictly in numeric order and record rollout evidence.
- Never edit an already-deployed migration; add the next numbered migration.
- Backward-incompatible changes require an expand/migrate/contract rollout.
- Unique idempotency constraints and approval-consumption semantics are correctness controls and must not be weakened.
- Strategy `(name, version)` identity is immutable; a published version must not be silently redefined.
- Outbox delivery is at-least-once. Consumers should deduplicate using the stable outbox message ID/header.
- Test backup/restore and rollback procedures before production schema changes.
