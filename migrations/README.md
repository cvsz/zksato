# Database migrations

`0001_core.sql` is the managed PostgreSQL baseline for zksato v0.3. The application also calls SQLAlchemy `metadata.create_all()` as a safe local/bootstrap mechanism, but production deployments should apply versioned SQL migrations explicitly before starting a new application release.

Example:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f migrations/0001_core.sql
```

Rules:

- Never edit an already-deployed migration; add the next numbered migration.
- Backward-incompatible changes require an expand/migrate/contract rollout.
- Unique idempotency constraints and approval-consumption semantics are correctness controls and must not be weakened.
- Test backup/restore before production schema changes.
