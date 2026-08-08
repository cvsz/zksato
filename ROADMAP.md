# zksato Roadmap

## Current release — v0.4 P0-P7 repository/source completion

All repository-controlled P0-P7 work is implemented or represented by fail-closed control/evidence gates. Items requiring a broker account, legal/operational approval, GitHub-plan features, production infrastructure, or measured external deployment evidence remain explicitly external and cannot be self-certified by source code.

### P0 — Durable correctness
- [x] PostgreSQL/SQLAlchemy system of record for trading state, risk/audit, idempotency, outbox and historical bars
- [x] versioned migrations and restart-safe `client_order_id` uniqueness
- [x] persistent paper state, durable fills/events, reconciliation readiness and ambiguous-outcome handling
- [x] optional Redis distributed coordination with local safe fallback
- [x] PostgreSQL + Redis CI integration, migration/restart/idempotency/reconciliation tests

### P1 — Trusted market data and deterministic risk
- [x] supervised Settrade realtime subscriptions with reconnect backoff
- [x] quote freshness, gap/out-of-order diagnostics and stale-feed execution guard
- [x] trusted portfolio/account-derived risk context
- [x] gross/net/symbol/sector/open-order/daily-order/loss/drawdown/notional/spread controls
- [x] explicit account allow-list, market-session enforcement, tick/price-band reference data
- [x] one-time intent-bound approvals downstream of deterministic risk

### P2 — Security and operator controls
- [x] API-key RBAC, signed HttpOnly sessions and CSRF
- [x] CORS/trusted-host/CSP/HSTS/security headers and coordinated rate limits
- [x] secret-file loading/rotation, tamper-evident audit chain and redacted audit API
- [x] optional four-eyes live approval; legacy reusable live token disabled by readiness policy

### P3 — TFEX isolation and semantics
- [x] dedicated LONG/SHORT and OPEN/CLOSE/AUTO domain
- [x] TFEX account/portfolio/order read gateway and contract metadata registry
- [x] contract/margin/stale/tick/expiry risk controls and settlement P&L helper
- [x] sandbox/UAT-only TFEX mutation boundary
- [ ] installed-SDK and broker-account TFEX behavior certified in Settrade UAT — **external evidence required**

### P4 — Observability, resilience and recovery
- [x] Prometheus metrics, correlation/JSON logging and optional OpenTelemetry exporter
- [x] Prometheus scrape/alert config and SLO definition
- [x] PostgreSQL backup/restore scripts, DR runbook and automated checksum/corruption/restore evidence workflow
- [x] bounded performance probe with explicit failure/p95 limits and JSON evidence
- [x] deterministic reconciliation/failure-path suite across multiple hash seeds
- [ ] production alert delivery, restore drill, measured production RPO/RTO and sustained production load evidence — **external deployment evidence required**

### P5 — Strategy research and promotion
- [x] durable OHLCV, deterministic replay and cost-aware backtesting
- [x] session-aware walk-forward/OOS reporting
- [x] strategy/version registry, code/config hash, promotion gates and drift primitive
- [x] broad deterministic indicator tests
- [ ] strategy-specific performance evidence — **research evidence, not a code-completion claim**

### P6 — Controlled production rollout
- [x] machine-readable production-readiness report and one-order non-autonomous canary plan
- [x] runtime gates for prod/live mode, durable services, auth, trusted hosts, confirmations, allow-list/reference/session controls, Settrade config, kill switch, reconciliation and audit integrity
- [x] external evidence model for broker/legal/UAT/TLS/secrets/DR/monitoring/incident/rollback/capacity/time-sync/market-data-failover/data-retention/release/manual-canary approval
- [x] protected non-mutating UAT and production-readiness workflows
- [ ] broker permission/legal sign-off, Settrade UAT certification, production TLS/secrets/monitoring/backup evidence and authorized minimal live canary — **external**

### P7 — Repository assurance and software supply chain
- [x] Python 3.11-3.14 matrix, PostgreSQL/Redis integration and branch coverage ratchet
- [x] Ruff lint/format, full mypy, Hypothesis risk properties and safety-critical OpenAPI contract
- [x] package build/twine/version identity and runtime dependency license inventory/policy
- [x] runtime pip-audit, Bandit, Gitleaks and secret-pattern scanning
- [x] full-SHA external Actions, least-privilege permissions, actionlint/yamllint/zizmor/ShellCheck/Hadolint
- [x] minimal multi-stage non-root Docker build, hardened runtime checks, Trivy CVE gate and image SBOM
- [x] multi-architecture GHCR release, dependency/image SBOMs, immutable digest, checksums, provenance and independent release verification
- [x] repository-health capability evidence, PR policy, safe path labeler and Dependabot for Python/Actions/Docker
- [x] documented developer parity through Make/pre-commit/editor/linter policies
- [ ] protected `uat`/`production` GitHub environments — **external repository setting**
- [ ] main branch protection/ruleset/merge queue — **GitHub plan/settings dependent**
- [ ] GitHub native Code Security/Secret Protection/Dependency Review/attestations — **plan/settings dependent**

## Non-negotiable invariant

**Autonomous live-money execution remains forbidden by design.** AI, agents, workflows and strategies may research, rank, explain, paper-trade and operate in broker UAT, but a live equity mutation requires deterministic server-side risk plus explicit operator authorization. TFEX mutation remains UAT-only until its external certification gate is completed.
