# Skill: deployment operations

## Workflow
Build immutable artifact → validate config/secrets → run migrations safely → deploy health/readiness → smoke test port `9569` → monitor → rollback if gates fail.

Separate dev/UAT/prod. Never bake secrets into images. Record release version/commit. Test backup/restore and broker reconciliation after restart.
