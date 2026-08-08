# zksato Roadmap

## Current release — v0.3 production-completion foundation

Implemented in code:

- [x] FastAPI control plane/dashboard on `9569`
- [x] paper execution, protective exits and persistent paper-account state
- [x] PostgreSQL/SQLAlchemy durable operational state
- [x] restart-safe order idempotency constraint
- [x] ambiguous broker-outcome state and reconciliation worker
- [x] durable notification outbox
- [x] migration baseline
- [x] deterministic advanced equity risk including stale-feed/spread/exposure/open-order limits
- [x] Settrade v2 equity adapter and realtime price/bid-offer bridge
- [x] deterministic scanner and expanded indicators
- [x] commission/slippage-aware backtesting
- [x] API-key RBAC and HTTP hardening
- [x] one-time intent-bound live approval with optional four-eyes separation
- [x] Prometheus-compatible metrics
- [x] dedicated TFEX domain, risk controls, read APIs and UAT-only mutation gateway
- [x] CI with PostgreSQL migration/integration validation
- [x] agent/skill/documentation/GitHub governance system

## Gate A — Settrade UAT certification

This requires real broker-provided UAT credentials and cannot be completed from source code alone.

- [ ] certify equity account/portfolio/order mappings against installed `settrade-v2`
- [ ] verify place/cancel/reconciliation under accepted, rejected, partial-fill and timeout paths
- [ ] run long-lived realtime feed tests including disconnect/reconnect behavior
- [ ] certify TFEX account/portfolio/order mappings and installed SDK mutation signature
- [ ] verify TFEX margin/contract/position semantics with broker UAT
- [ ] retain sanitized UAT evidence and sign-off

**Exit:** every broker mutation and reconciliation assumption used in production has reproducible UAT evidence.

## Gate B — Production infrastructure

Deployment-dependent work:

- [ ] external TLS/reverse proxy or ingress
- [ ] managed secret store/KMS and rotation process
- [ ] production PostgreSQL high availability/backup policy
- [ ] backup restore drill with measured RPO/RTO
- [ ] centralized logs and traces (OpenTelemetry/Loki or equivalent)
- [ ] Prometheus scraping, Grafana dashboards and actionable alerts
- [ ] external identity/SSO if service is multi-user/internet exposed
- [ ] distributed rate limiting/coordination if horizontally scaled
- [ ] vulnerability/SBOM/container scanning in the target registry pipeline

## Gate C — Research maturity

- [ ] durable historical OHLCV/replay store
- [ ] walk-forward/out-of-sample reporting
- [ ] strategy/parameter version registry
- [ ] paper-vs-backtest drift reports
- [ ] market-session/tick-size/price-band reference integration
- [ ] optional sector concentration model backed by trusted instrument metadata

## Gate D — Controlled production rollout

- [ ] confirm broker permissions, legal/operational requirements and account allow-list
- [ ] run live in signal-only mode first
- [ ] verify risk-admin -> one-time approval -> distinct order-approver workflow
- [ ] tiny-capital manual-confirmation canary
- [ ] reconcile expected vs broker orders/fills/positions every session
- [ ] run kill-switch and incident exercises
- [ ] increase limits only from reviewed evidence

## Deliberate non-goal

**Autonomous live-money execution remains forbidden by design.** Completing zksato does not mean removing this control. AI/agents/strategies may propose or automate paper/UAT actions, but live broker mutation remains explicitly operator-authorized through the trusted server boundary.
