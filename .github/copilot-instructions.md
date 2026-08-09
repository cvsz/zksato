# GitHub Copilot instructions for zksato

Read `/AGENTS.md`, `/SECURITY.md`, and `/docs/INDEX.md` before editing. Preserve the risk-first architecture and API/dashboard port `9569`.

Never generate code that exposes broker credentials, bypasses server-side risk/auth/reconciliation, grants an LLM/agent unrestricted broker mutation, restores stale broker-readiness state after restart, or enables autonomous live-money execution. TFEX production mutation remains blocked until separately certified.

For Python changes: keep domain logic typed/deterministic, use explicit error handling, add pytest coverage, and satisfy Ruff format/lint plus mypy. For stateful/trading changes: document failure modes, idempotency, restart/reconciliation, audit/observability, migration, rollout, rollback, and paper/UAT evidence.

Use `docs/templates/` for ADR/RFC/change/security/risk/strategy/migration/UAT/incident/DR/performance/readiness evidence. Distinguish implemented source capability from external GitHub, broker, deployment, legal, or production evidence.
