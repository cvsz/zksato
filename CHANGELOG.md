# Changelog

All notable changes are recorded using Keep a Changelog principles and semantic versioning where practical.

## [Unreleased]

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
- Package version advanced to `0.3.0`.
- Live reusable confirmation tokens are disabled by default in favor of one-time approvals.

## [0.2.0]

### Added
- Automated paper/UAT trading platform, risk engine, Settrade v2 adapter, backtesting, alerts, audit trail, dashboard, agent/skill documentation system and operations documentation.

### Changed
- Service/dashboard port moved to `9569`.
