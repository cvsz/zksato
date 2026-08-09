# Non-functional requirements

## Safety and correctness
NFR-001 money-moving behavior is deterministic and auditable.
NFR-002 all execution boundaries fail closed on missing trust prerequisites.
NFR-003 idempotency/reconciliation prevent duplicate economic execution.

## Security
NFR-010 secrets remain server-side and are redacted from APIs/logs/audit.
NFR-011 least privilege applies to RBAC, GitHub Actions, deployment identities, and broker credentials.
NFR-012 security-sensitive changes receive explicit review and evidence.

## Reliability
NFR-020 PostgreSQL is the durable correctness boundary when configured; Redis is coordination, not the source of truth.
NFR-021 restart behavior is tested for durable state and freshness-only state.
NFR-022 background failures are bounded, observable, retryable where safe, and must not silently authorize execution.

## Performance
NFR-030 API and background work must meet documented SLOs under validated capacity.
NFR-031 trading-path work must not block on optional notification delivery.

## Maintainability
NFR-040 Python 3.11+ compatibility, static checks, branch coverage, documented architecture, ADRs, migrations, and runbooks are maintained.
NFR-041 source-controlled behavior must be reproducible from repository history without dangling/unreviewed artifacts.

## Operability
NFR-050 liveness/readiness/metrics/logging/tracing support diagnosis.
NFR-051 releases include rollback guidance and production claims require environment evidence.
