# Changelog

All notable changes are recorded using Keep a Changelog principles and semantic versioning where practical.

## [Unreleased]

### Added
- Hardened GitHub Actions suite with immutable full-SHA action pins, explicit token permissions, concurrency controls, timeouts, and Node 24-generation core actions.
- Python 3.11-3.14 compatibility CI in addition to the PostgreSQL/Redis integration gate.
- Security workflow with `pip-audit`, Bandit, high-confidence credential-pattern scanning, and capability-gated CodeQL.
- Docker build/non-root/runtime health validation workflow.
- Capability-gated GitHub Dependency Review workflow for supported repository plans.
- Bounded scheduled/manual performance evidence workflow.
- Monthly/manual PostgreSQL backup-checksum-restore disaster-recovery drill.
- Protected, non-mutating Settrade UAT certification workflow and evidence artifact.
- Tag-driven release workflow with dependency audit, clean wheel installation, CycloneDX SBOM, SHA-256 checksums, optional artifact attestation, and GitHub Release creation.
- Expanded GitHub Actions operating documentation, required-check guidance, repository variables, protected environment requirements, and release policy.

### Changed
- Dependabot Python and GitHub Actions updates are grouped and scheduled in the `Asia/Bangkok` timezone.
- Existing `CI` and `Governance` workflows now use pinned current-generation Actions and stronger fail-closed policy checks.

## [0.4.0]

### Added
- P0 durable order events, fills, risk evaluations, account snapshots, historical bars, strategy versions/runs, and PostgreSQL migration `0002_priority_state.sql`.
- Redis-backed coordination locks and distributed rate-limit state with local fallback.
- Reconciliation readiness persistence, convergence gating, durable reconciliation events, and fill recovery.
- Trusted instrument metadata, exchange-session policy, account allow-list, price-band/tick validation, and net/sector exposure controls.
- Supervised Settrade realtime reconnect/backoff plus freshness, gap, and out-of-order diagnostics.
- HMAC-signed expiring HttpOnly sessions and CSRF protection.
- Secret-file loading, tamper-evident audit chaining, sensitive-data redaction, CSP/HSTS hardening, and secret-rotation runbook.
- TFEX contract metadata, expiry/tick controls, settlement helper, and strict reference-data option while preserving the UAT-only mutation boundary.
- JSON correlation logging, optional OpenTelemetry traces, SLO metrics, Prometheus alert configuration, DR scripts, and bounded load probe.
- Durable OHLCV replay, session-aware walk-forward/OOS research, strategy/version registry, drift primitive, and staged promotion evidence gates.
- Machine-readable production-readiness and non-executing canary-plan controls plus independent durable-fill versus broker-position session reconciliation.
- UAT, production-readiness, secrets, SLO, and disaster-recovery runbooks.
- CI Redis service, compile validation, all-migration execution, dependency consistency, and expanded tests.

### Changed
- Package/API version advanced to `0.4.0`.
- P0-P6 repository-controlled completion is tracked separately from broker/deployment evidence.
- Autonomous live-money execution remains forbidden and TFEX mutation remains UAT-only.

## [0.3.0]

### Added
- PostgreSQL/SQLAlchemy durable operational state and migration baseline.
- Restart-safe client order idempotency and persistent paper account recovery.
- Broker ambiguity classification and reconciliation worker.
- Durable webhook outbox.
- Settrade realtime price/bid-offer bridge and deterministic scanner.
- ATR, ADX, Bollinger Bands and VWAP indicators.
- Commission/slippage-aware backtesting.
- API-key RBAC, HTTP rate limiting, CORS/trusted-host configuration and security headers.
- One-time intent-bound live approval flow with optional four-eyes separation.
- Prometheus-compatible metrics.
- Dedicated TFEX domain, risk model, read APIs and UAT-only mutation boundary.
- PostgreSQL migration/integration validation in CI.

### Changed
- Live reusable confirmation tokens are disabled by default in favor of one-time approvals.

## [0.2.0]

### Added
- Automated paper/UAT platform, deterministic risk engine, Settrade v2 adapter, backtesting, alerts, audit trail, dashboard, agent/skill documentation system, and operations documentation.

### Changed
- Service/dashboard port moved to `9569`.
