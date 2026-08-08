# Testing strategy

## Required baseline
`ruff check .` and `pytest` on every PR.

## Test pyramid
- Unit: indicators, strategy, risk, accounting, mapping.
- State/property: order lifecycle, idempotency, portfolio invariants.
- API contract: validation/auth/error semantics.
- Integration: PostgreSQL/Redis/outbox/repositories.
- Resilience: restart, timeout, duplicate, broker/feed/DB failures.
- Broker UAT: place/query/change/cancel/fills/reconciliation.
- Performance: feed/order/reconciliation latency and sustained load.
- Security: authz bypass, CSRF/CORS/rate, secret leakage.

## Must-have trading failure cases
Timeout after broker acceptance, duplicate request, partial fill, cancel race, stale feed, unknown session, kill switch, drawdown breach, broker/local drift, process restart.

Tests must avoid real production broker mutations.
