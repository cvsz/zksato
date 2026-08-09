## Summary

## Why

## Scope

## Related issue / ADR / RFC

## Risk / execution impact
- [ ] No money-moving behavior changes
- [ ] Risk policy changes
- [ ] Broker/execution/reconciliation changes
- [ ] Order identity/idempotency changes
- [ ] Portfolio/P&L changes
- [ ] Market/reference-data changes
- [ ] Auth/secrets/security changes
- [ ] Database migration/durable state changes
- [ ] TFEX changes
- [ ] CI/CD/deployment changes

State the protected or changed invariant:

## Validation
- [ ] compile / dependency consistency
- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] mypy
- [ ] pytest/coverage
- [ ] OpenAPI contract (if applicable)
- [ ] PostgreSQL/Redis integration (if applicable)
- [ ] Docker/container validation (if applicable)
- [ ] security/dependency scans (if applicable)
- [ ] paper validation
- [ ] broker UAT evidence (only when applicable)

Evidence/run links:

## Data / migrations

## Observability / audit

## Rollout

## Rollback

## Documentation
- [ ] docs/index/contracts updated
- [ ] feature matrix/roadmap updated if capability state changed
- [ ] ADR/RFC updated if architectural
- [ ] runbook/checklist updated if operational
- [ ] changelog/release notes updated when required

## Security checklist
- [ ] no secrets/account-sensitive data in code/logs/UI/artifacts
- [ ] authorization checked server-side
- [ ] failure mode is fail-closed where required
- [ ] idempotency/reconciliation reviewed
- [ ] autonomous live-money execution remains forbidden
- [ ] TFEX production mutation remains blocked unless separately certified

## External gates
List broker, GitHub-plan, environment, legal, TLS/secrets, monitoring, DR, capacity, or canary evidence that remains external. Do not mark intended configuration as completed evidence.
