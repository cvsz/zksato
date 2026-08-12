# zksato Roadmap

## Current release — v0.6.0 Infrastructure, TFEX, UI, and AI

Now that v0.5 has perfected the local runtime and tests, v0.6.0 focuses on real-world broker certification, production deployment, and advanced intelligence.

### P9 — Infrastructure and Production Deployments (External)
- [ ] Infrastructure as Code (Terraform) for AWS/GCP with KMS encryption
- [ ] OpenTelemetry collector + Grafana/Prometheus deployment
- [ ] RPO/RTO disaster recovery drills

### P10 — TFEX Broker Certification
- [ ] Migrate Settrade simulator to Settrade UAT sandbox
- [ ] Contract rollover and dynamic margin management

### P11 — Secure Operator Dashboard
- [ ] Frontend dashboard built for operator interaction
- [ ] One-time manual risk approval via webhook pagers

### P12 — AI-Augmented Research
- [ ] LLM Sentiment signals integrated into `strategy.py`
- [ ] Agentic parameter sweep exploration inside `video_ea_research.py`

## Previous release — v0.5 P0-P8 repository/source completion
- [x] PostgreSQL/SQLAlchemy system of record for trading state, evidence, idempotency, outbox and historical bars
- [x] versioned migrations and restart-safe `client_order_id` uniqueness
- [x] persistent paper cash/holdings/P&L, durable lifecycle events and reconciliation readiness
- [x] optional Redis coordination with PostgreSQL correctness boundary

### P1 — Trusted market data and deterministic risk
- [x] supervised Settrade realtime subscriptions with reconnect/freshness/gap diagnostics
- [x] trusted portfolio/account/quote/reference-derived risk context
- [x] gross/net/symbol/sector/open-order/daily-order/loss/drawdown/notional/spread controls
- [x] account allow-list, tick/price-band and market-session enforcement
- [x] one-time intent-bound approvals downstream of deterministic risk

### P2 — Security and operator controls
- [x] API-key RBAC, signed HttpOnly sessions and CSRF
- [x] CORS/trusted-host/CSP/HSTS/security headers and coordinated rate limits
- [x] secret-file loading, redaction and tamper-evident audit chain
- [x] optional four-eyes live approval

### P3 — TFEX isolation and semantics
- [x] dedicated LONG/SHORT and OPEN/CLOSE/AUTO domain
- [x] TFEX account/portfolio/order reads, contract registry and deterministic risk
- [x] sandbox/UAT-only TFEX mutation boundary
- [ ] installed-SDK and broker-account behavior certified in Settrade UAT — **external**

### P4 — Observability, resilience and recovery
- [x] Prometheus, correlation/JSON logging and optional OpenTelemetry
- [x] SLO/alert configuration, load probe and resilience matrix
- [x] backup/checksum/corruption/restore automation and DR runbook
- [ ] production alert delivery, restore/RPO/RTO and sustained-load evidence — **external**

### P5 — Strategy research and promotion
- [x] durable OHLCV, replay, cost/slippage backtesting and session-aware walk-forward/OOS
- [x] strategy/version registry, run history, config hash, drift and promotion gates
- [x] deterministic indicator/strategy test coverage
- [ ] strategy-specific investment-performance evidence — **research evidence, not source completion**

### P6 — Controlled production rollout
- [x] machine-readable readiness report and one-order non-autonomous canary plan
- [x] fail-closed runtime/external evidence requirements
- [x] protected non-mutating UAT/readiness workflows
- [ ] broker/legal/UAT/TLS/secrets/monitoring/backup and authorized manual canary — **external**

### P7 — Repository assurance and software supply chain
- [x] Python 3.11-3.14, PostgreSQL/Redis integration and branch coverage ratchet
- [x] Ruff/format/mypy/Hypothesis/OpenAPI contract/package/license gates
- [x] pip-audit/Bandit/Gitleaks/workflow-security checks
- [x] hardened non-root container, Trivy CVE gate and SBOM
- [x] multi-arch GHCR release, digest/checksums/provenance and release verification
- [x] repository health, PR policy, safe labeler and Dependabot
- [ ] protected environments/ruleset/merge queue/native code-security capabilities — **GitHub plan/settings dependent**

### P8 — Execution simulator, calendar, research and operator API completion
- [x] resting paper limits match on later quotes
- [x] deterministic per-quote partial fills, weighted average fills and quote-side price improvement
- [x] restart-safe paper client IDs and cancellation of partially-filled remainders
- [x] cumulative broker snapshots converted to incremental durable fill records
- [x] reconciliation/cancellation preserve local order economic identity
- [x] configurable holiday/special-session overrides with explainable session state
- [x] EMA/SMA cross, RSI/Bollinger reversion, momentum, MACD and breakout strategies
- [x] MACD, rate-of-change and realized-volatility indicators
- [x] backtest fee/exposure/profit-factor/benchmark analytics
- [x] bot pause/resume and quote-driven paper matching
- [x] liveness/readiness and request correlation IDs
- [x] order detail/filtering and safe bulk cancellation of open orders
- [x] account snapshot history and market-session diagnostics APIs
- [x] strategy registry/run history, historical-bar read and drift APIs
- [x] notification outbox poison-message isolation
- [x] OpenAPI safety contract extended for the new control surface

## Non-negotiable invariant

**Autonomous live-money execution remains forbidden by design.** AI, agents, workflows and strategies may research, rank, explain, paper-trade and operate in broker UAT, but live equity mutation requires deterministic server-side risk plus explicit operator authorization. TFEX mutation remains UAT-only until external certification is complete.
