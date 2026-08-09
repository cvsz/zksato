# Changelog

All notable changes to zksato are documented here.

## Unreleased

### Durable operations and research identity
- Added durable webhook delivery attempt state with bounded exponential retry scheduling, terminal dead-letter state, and explicit requeue support.
- Persisted outbox retry/dead-letter evidence across SQL-backed restarts with PostgreSQL migration `0003_outbox_delivery.sql`.
- Added stable `X-ZKSATO-Outbox-Id` delivery identity so at-least-once webhook consumers can deduplicate safely.
- Prevented webhook URLs, query tokens, and payload details from being persisted in notification failure diagnostics.
- Added bounded handling for poison/serialization failures so one invalid notification cannot terminate the dispatcher loop.
- Made strategy `(name, version)` identity immutable and idempotent across memory and SQL stores, aligned with the PostgreSQL uniqueness constraint.
- Added regression coverage for retry timing, dead-lettering, restart recovery, error redaction, poison payloads, and strategy-version conflicts.

### v0.5 execution/research/operator completion
- Added restart-safe paper resting-limit matching against later quotes instead of leaving non-marketable limits permanently accepted.
- Added configurable deterministic per-quote partial fills, weighted cumulative average prices, quote-side price improvement, and cancellation of partially-filled remainders.
- Added delta-correct durable fill accounting so cumulative broker reconciliation snapshots do not double-count earlier fills.
- Hardened broker reconciliation and cancel merges to preserve local immutable order identity and economic intent.
- Added configurable exchange holiday and special-session overrides plus explainable market-session diagnostics.
- Expanded deterministic strategy catalog with SMA cross, Bollinger reversion, momentum, and MACD cross alongside EMA/RSI/breakout.
- Added MACD, rate-of-change, and realized-volatility indicators.
- Expanded backtest evidence with per-trade fees, closed-trade counts, gross profit/loss, profit factor, average closed P&L, exposure, and buy-and-hold benchmark.
- Added bot pause/resume, liveness/readiness endpoints, response correlation IDs, order detail/filtering, safe bulk cancel-open, account snapshot history, research bar reads, strategy registry/run history, and drift API.
- Changed notification dispatch so one failed durable webhook message does not block unrelated messages in the same batch.
- Extended OpenAPI safety-contract coverage for the new operator/research surface.

### Repository assurance and delivery
- Added full engineering assurance: Ruff format/lint, mypy, branch coverage, Hypothesis safety invariants, OpenAPI contract validation, package metadata, and runtime license policy.
- Added immutable Action SHA checks, YAML/actionlint/zizmor/ShellCheck/Hadolint validation, PR policy and safe path labeling.
- Added pip-audit, Bandit, Gitleaks, hardened container runtime, Trivy fixed-critical gate, SBOMs, multi-architecture GHCR release, checksums/provenance, release verification, DR/performance evidence, and repository capability reporting.

## 0.4.0
- P0-P7 risk-first platform and repository-assurance baseline with durable state, reconciliation, trusted market/risk controls, RBAC/approvals, TFEX UAT isolation, observability/DR, research promotion, non-executing production readiness, and hardened supply-chain workflows.
- Production port standardized on `9569`.
- Autonomous live-money execution remains forbidden by design.
