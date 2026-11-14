# Changelog

All notable changes to zksato are documented here.

## [1.1.0] - 2026-11-14 — Agent Engineering Platform (Phase 4) + Build Repair

### Agent Engineering Platform (Phase 4)
- **Orchestrator v2** (`OrchestratorV2`) — async multi-agent task engine with capability-based
  routing across five specialized agents (Architect, Security Auditor, Code Reviewer, Test Engineer,
  Documentation), priority queue, dependency resolution, heartbeat monitoring, and a persistent task store.
- **A2A protocol** — agent-to-agent messaging with capability advertisement, registry, request/response
  envelopes, and handler dispatch (`agent_os.a2a.protocol`).
- **Hooks framework** — lifecycle events, execution priorities, conditions, per-hook timeouts, built-in
  logging/safety hooks, and audit logging (`zksato_cli.hooks.framework`).
- **Context management** — token budgeting, compaction (importance/recency/size), deduplication,
  relevance ranking, and cross-session JSON persistence (`zksato_cli.context.manager`).
- **Sessions** — JSONL session store with checkpoints, interrupted-session recovery, and export/import.
- **Skills system** — manifest validation, scoped registries, entry-point execution, and built-in skills
  (`grep`, `read-file`).
- **Plan mode** — dependency-graph plans with ready-set computation, approval gates, phase tracking, and
  persistence (`zksato_cli.planning.plan_mode`).
- **MCP integration** — Model Context Protocol client and server with stdio/SSE/WebSocket transports,
  tool/resource/prompt discovery, and manager config persistence (`zksato_cli.mcp`).
- **CRDT shared state** — G/PN counters, LWW registers, and OR-sets with merge-convergence semantics
  (`agent_os.coordination.shared_state`).

### Build & tooling repair
- Restored root `pyproject.toml` build backend (hatchling) so `pip install -e .` provides the legacy
  `import zksato`; reinstated `dev/quality/security/settrade/ccxt/prediction/observability` extras.
- Reverted the accidental Python `>=3.12` floor back to the AGENTS.md-mandated `>=3.11`.
- Extended ruff/format/mypy/bandit gates across `packages/` (10 workspace packages).
- Fixed real runtime bugs found by the new linters: undefined `Callable`/`asyncio`/`timedelta` imports,
  a late-binding lambda loop capture, an unpersisted background-task reference, and a duplicate dict key.

### Testing & coverage
- New `tests/test_agent_platform.py` — 48 tests covering orchestrator e2e, A2A registry/messages, hooks
  (registration/priority/conditions/builtins/timeout), context budget/compaction/dedup/persistence,
  sessions (create/checkpoint/recovery/export/import/delete), skills (manifest/registry/builtins),
  plan mode (dependencies/ready-set/persistence/phases), MCP (envelopes/transports/manager), CRDT
  merge convergence, and the five specialized agents.
- Full suite: **690 passed, 6 skipped**; root `zksato` coverage **65.51%** (gate ≥65%).
- Makefile modernized: correct monorepo install (leaf-first), `packages/` in bandit scope, duplicate
  `.PHONY` removal, `test-agent-platform` target, artifact-aware `clean`.

### Deferred (tracked in `PHASE4_PLAN.md`)
- Git worktree integration, LSP diagnostics, PII redaction, and the production conflict resolver
  (file ownership is tracked; `resolve_conflict` is currently a stub).

## [1.0.1] - 2026-11-12 — Enterprise Production Validation

### Testing & Coverage
- **Overall test coverage: 65.07%** (target ≥65%) — up from ~62%
- **Total tests: 486 passed** (up from 389) — +97 new tests
- Added comprehensive test suites for previously under-covered modules:
  - `tests/test_protections.py` (20 tests): All 6 protection mechanisms (Cooldown, StoplossGuard, Drawdown, Volatility, TimeBased, ConsecutiveLoss) + integration tests — coverage 27%→96%
  - `tests/test_trailing_stop.py` (29 tests): Trailing stop logic, activation thresholds, long/short positions, configuration edge cases — coverage 25%→98%
  - `tests/test_prediction_live.py` (35 tests): Polymarket CLOB adapter, live gate, authentication, quote fallbacks, order placement/cancellation — coverage 59%→86%
  - `tests/test_prediction_feed.py` (13 tests): Reference price refresh, tick generation, crypto/non-crypto filtering, callbacks — coverage 49%→73%
  - `tests/test_reconcile.py` (14 tests): Broker reconciliation, ambiguous outcomes, coordination locks, worker lifecycle — coverage 56%→93%
  - `tests/test_secrets.py` (23 tests): AWS Secrets Manager source, .env validation (shell metacharacters, placeholders, secret keys) — coverage 51%→82%
  - `tests/test_prediction_live.py` + `tests/test_reconcile.py` + `tests/test_secrets.py` fixes for async coordination, time-based stop period expiry, import ordering

### Type Safety & Code Quality
- **mypy --strict**: 0 errors across 77 source files (fixed all `type: ignore` comments in `indicators.py` and `security.py`)
- **ruff**: Core code clean; minor style issues remain in test files only
- Removed unused `type: ignore[no-any-return]` comments from indicator series functions
- Fixed `datetime.datetime` unused import warnings

### Security & Hardening
- Enhanced `.env` validation in `secrets.py`: allows `${...}` placeholder syntax for secret keys while still blocking shell metacharacters
- AWS Secrets Manager source (`AWSSecretManagerSettingsSource`) tested for cache, env fallback, boto3 missing, and client errors
- **bandit**: 0 HIGH/MEDIUM findings; 23 LOW (asserts in internal checks, demo random, secret file names)
- **pip-audit**: 0 known vulnerabilities in dependencies (pip upgraded to 26.3)

### Reliability & Data Integrity
- Fixed `ReconciliationWorker` stop period handling: worker now properly tracks reconciliation readiness
- Improved `ProtectionManager` record_trade_exit: correctly resets consecutive losses on winning trades
- Fixed `StoplossGuardProtection` and `ConsecutiveLossProtection` stop period expiry logic

### Risk & Prediction
- Polymarket CLOB adapter: fixed quote fallback chain (book → price → markets endpoints)
- Added proper async context manager usage for coordination locks in reconciliation tests
- Prediction market feed: reference price refresh for Binance/KuCoin, synthetic fallback, stale detection

### Developer Tooling
- **Created `Final-Report.md`** with complete validation evidence, coverage tables, and sign-off workflow
- All validation gates pass: dependencies, linting (core), type safety, tests (486), coverage (65.07%), Docker Compose config, container security, workflow security
- Updated `docs/API-SPEC.md` with environment-specific behavior for `/v1/live-approvals`, `/v1/production/readiness`, and `/v1/orders`.
- Updated `ROADMAP.md` with detailed status and blockers for incomplete external-gate items.
- Fixed `tests/test_postgres_integration.py` to load `.env` via `python-dotenv`.

### Broker Integration
- Added `SettradeError` propagation in `SettradeBroker.__init__` preserving `.code` and `.status_code`.
- Fixed `portfolio()` to handle string-encoded portfolio rows from Settrade SDK.
- Added `account()` wrapper for `get_account_info`.

### Infrastructure
- Installed global PostgreSQL 18 on port 5433 for integration testing.
- Configured `docker compose` restart policy to `unless-stopped` for zksato stack.
- Validated multi-stage Dockerfiles (api, frontend, dashboard) with hadolint — 0 errors
- GitHub Actions workflows secured with immutable SHA pins, zizmor validation

### Documentation Sync
- `README.md`: v1.0.1 features, quick start, deployment
- `AGENTS.md`: Operating contract, invariants, Git governance
- `ROADMAP.md`: P9-P14 complete, external gates documented
- `docs/FEATURE-MATRIX.md`: 96 capabilities mapped
- `docs/ARCHITECTURE.md`: Trust boundaries, components, data flow
- `docs/API-SPEC.md`: All endpoints with environment behavior
- `docs/DATABASE.md`: Schema, migrations, idempotency
- `SECURITY.md`: Threat model, vulnerability handling
- `CONTRIBUTING.md`: Validation workflow, PR requirements

## [1.0.1] - 2026-08-31

### Post-release fixes
- **Quality:** Resolved mypy type errors across 58 source files; removed stale `# type: ignore` comments; fixed `available_quantity` and `filled_quantity_recorded` type mismatches.
- **Testing:** Eliminated skipped PostgreSQL integration test by configuring `ZKSATO_TEST_DATABASE_URL` for Dockerized Postgres; 327 tests passing with 71.25% coverage.
- **Documentation:** Updated external-gate evidence templates (`PRODUCTION-READINESS-EVIDENCE.md`, `UAT-EVIDENCE.md`), enhanced DR runbook with quarterly drill checklist, added operator handoff document, and marked release evidence complete.

## [1.0.0] - 2026-08-31

### Final Production Release & USDT Self-Hosting
- **Native Python Agent OS:** Decoupled, zero-MCP agent framework featuring partitioned sub-accounts (`AgentSubAccount`), hardcoded `WITHDRAW = False` safety invariants, and an extensible `AgentSkillHub` registry.
- **Agent OS REST Control Plane:** Exposed `/v1/agent-os/skills`, `/v1/agent-os/subaccounts`, and `/v1/agent-os/execute` routes on the FastAPI control plane with strict pre-trade `RiskEngine` boundaries.
- **CPMM Liquidity Depth & Dynamic Slippage:** Integrated `LiquidityPool` model into prediction markets, computing non-linear price impact, basis-point slippage, and swap executions.
- **Binance TH (Thailand) Spot Execution:** Added official support and symbol mappings for Thai Baht fiat spot pairs (`BTC/THB`, `USDT/THB`, `ETH/THB`, `BNB/THB`) via `binanceth` venue.
- **WebSocket Supervisor with Jittered Backoff:** Added randomized uniform jitter and exponential backoff to public market stream reconnections.
- **USDT-First Self-Hosting:** Full-stack localhost Docker Compose runtime with FastAPI backend, PostgreSQL system-of-record, Redis coordination, and Next.js 16 frontend.
- **CCXT Multi-Exchange Adapter:** Multi-venue spot execution with sandbox mode support across Binance, Binance TH, KuCoin, OKX, and Bybit.
- **Prediction Markets Module:** Synthetic pricing feeds, directional residual limits, complete-set cost risk engine, and guarded live execution gate.
- **TradingView & Telegram Integration:** HMAC-SHA256 authenticated webhook alerting with automated signal dispatching, symbol-keyed configurations, and Telegram alert delivery.
- **Market Terminal:** Real-time dark-themed TradingView charting terminal with read-only sandbox mode and CSP headers.
- **Next.js Frontend:** Multi-lingual (EN, TH, JA, ZH) operator UI with Lightweight Charts, real-time risk gauges, session timeouts, and theme customizers.
- **Strategy & AI:** Added Agentic Walk-Forward Optimization, Multi-Factor strategy, Ichimoku Clouds, and News Ingestion Adapter for real-time external sentiment.
- **Security:** Integrated AWS Secrets Manager for centralized credential handling alongside local secret file loading and GPG encryption.
- **Infrastructure:** Added Nginx configuration for TLS/SSL support via certbot and completed sustained load testing scripts for Database/Store robustness.
- **Operations & Compliance:** Authored Broker Certification architecture docs, TFEX UAT scripts, Operator Agreement legal template, operator handoff document, and updated external-gate evidence templates.
- **Quality:** Resolved mypy type errors across 58 source files; removed stale `# type: ignore` comments; fixed `available_quantity` and `filled_quantity_recorded` type mismatches.
- **Testing:** Eliminated skipped PostgreSQL integration test by configuring `ZKSATO_TEST_DATABASE_URL` for Dockerized Postgres; 327 tests passing with 71.25% coverage.
- Reached official full completion of all Roadmap objectives for production readiness.

## [0.6.0] - 2026-08-12

### Infrastructure & Deployment
- Set `localhost` (Docker Compose) as the primary execution environment.
- Added OpenTelemetry collector, Prometheus, and Grafana for local monitoring.
- Created Terraform AWS/GCP templates for backup/cloud deployment.
- Wrote full `DR-DRILL.md` runbook for Disaster Recovery scenarios.

### Trading & TFEX
- Integrated Settrade UAT Sandbox for TFEX certification testing.
- Added dynamic margin management and contract rollover evaluation to `TfexRiskEngine`.

### Dashboard & UI
- Built a modern, premium React/Vite dashboard (`dashboard/`) for the operator control plane.
- Implemented real-time portfolio risk visualizations.
- Added the interactive "One-Time Manual Risk Approval" workflow for autonomous live-money intents.

### AI & Quant Research
- Added `_llm_sentiment` analyzer to `strategy.py` to evaluate natural language sentiment scores against strict risk thresholds.
- Created `agentic_parameter_sweep` in `video_ea_research.py` to allow AI agents to autonomously explore parameter distributions and optimize backtest performance.

## [0.5.0] - 2026-08-12
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


## v2.1.0 — Phase 5: LLM-Driven Decision Engine & Market Features

**Release Date**: Sat Nov 14 2026

### New Features
- Adapted anglerfish-fable5 autotrade.py features for zksato (LLM decision engine, market features, dashboard modules, bot CLI)
- Full Phase 5 implementation with performance optimization
- MIRO module registry for extensible dashboard UI modules
- NumPy-vectorized technical indicators (SMA, EMA, RSI, MACD, Bollinger, VWAP, ATR, Williams %R)
- Execution mode gate at resolve_execution_mode() — single decision point for live trading
- Safety-first design: DRY_RUN by default, fail-closed HOLD on any parse/error/network failure
- LLM is signal generator only; all order placement goes through RiskEngine
- Fail-closed: HOLD default on any parse/error/network failure
- Risk evaluation always goes through zksato RiskEngine before any order placement
- Dashboard uses Binance light theme adapted to zksato dark theme

### Performance
- Target: ~134k risk eval/sec, ~120k check_risk/sec, ~15k place_order/sec
- NumPy-vectorized indicator calculations
- Main loop throughput competitive with benchmarks

### Bug Fixes
- Reimplemented `packages/zksato-market/src/zksato_market/features.py` (was deleted during ruff fixing)
- Dashboard MIRO module integration
- Full pytest validation: 694 passed, no regressions

### Safety Invariants (all preserved)
1. `paper` is the default mode
2. Autonomous live-money execution is forbidden
3. No LLM/agent may bypass `RiskEngine` or `TradingService`
4. Broker credentials stay server-side, never committed/logged/returned by APIs
5. Broker state is the external source of truth; local state must converge to it
6. Order creation must be idempotent across retries
7. Stale/unknown market feed must fail closed for automated execution
8. Risk controls must have independent kill paths and failure-path tests
9. SET and TFEX semantics must not be conflated
10. Money-moving behavior must be deterministic, auditable, versioned, and testable

