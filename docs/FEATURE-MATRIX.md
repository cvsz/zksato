# Feature matrix

Status meanings: **Implemented** = repository code exists and is covered by automated/source validation; **External gate** = code/control exists but proof depends on broker, deployment, GitHub plan/settings, or operator evidence; **Intentionally unsupported** = prohibited by the risk model.

| Area | Capability | Status | Notes |
| --- | --- | --- | --- |
| Trading | Paper broker/order lifecycle | Implemented | market/limit/fill/cancel/idempotency paths |
| Trading | Portfolio/P&L and persistent paper recovery | Implemented | durable state when DB configured |
| Trading | Settrade v2 equity adapter | Implemented | broker UAT certification remains external |
| Trading | Confirmed manual live equity boundary | Implemented | deterministic risk + approval; not production-certified by source |
| Trading | Autonomous live-money execution | Intentionally unsupported | permanent safety invariant |
| Market data | External quote ingestion/demo feed | Implemented | paper/demo and API ingestion |
| Market data | Supervised Settrade realtime bridge | Implemented | reconnect/freshness/gap controls; long-running UAT evidence external |
| Market data | Durable OHLCV/scanner | Implemented | research/strategy support |
| Strategy | EMA/RSI/Breakout + indicators | Implemented | deterministic engine; broad indicator edge tests |
| Strategy | Cost-aware backtest/walk-forward/version registry | Implemented | strategy-specific performance evidence external |
| Risk | Pre-trade deterministic RiskEngine | Implemented | stale feed, position/notional/exposure/loss/drawdown/session/reference controls |
| Risk | Property-based fail-closed invariants | Implemented | kill switch, stale quote, sell inventory, max notional |
| Execution | Durable idempotency and reconciliation gate | Implemented | unknown broker outcomes require reconciliation |
| Security | RBAC/session/CSRF/browser hardening | Implemented | server-side authorization |
| Security | One-time intent-bound four-eyes approval | Implemented | live execution boundary |
| Security | Tamper-evident/redacted audit trail | Implemented | production readiness verifies chain integrity |
| TFEX | Isolated domain/risk/UAT mutation | Implemented | production mutation intentionally unavailable |
| TFEX | Real broker UAT certification | External gate | credentials/account/broker evidence required |
| Persistence | PostgreSQL durable system of record | Implemented | migrations validated on PostgreSQL 16 in CI |
| Coordination | Redis distributed coordination | Implemented | PostgreSQL remains correctness boundary |
| Observability | Metrics/logging/optional OTel/SLO config | Implemented | production delivery/alert evidence external |
| DR | Backup/restore automation and ephemeral drill | Implemented | checksum, corruption detection, sentinel and timing evidence |
| DR | Production restore/RPO/RTO evidence | External gate | must be measured in production-like environment |
| Performance | Bounded local hardened-container SLO probe | Implemented | explicit p95/failure threshold and JSON artifact |
| CI | Python 3.11-3.14 + Postgres/Redis integration | Implemented | migrations, compile, dependency consistency, tests |
| CI | Branch coverage ratchet | Implemented | current floor 65% |
| Quality | Ruff full-repo lint/format and mypy | Implemented | `src/zksato` + scripts |
| Quality | OpenAPI safety contract | Implemented | critical routes required; live-TFEX routes rejected |
| Quality | Package/twine/version identity | Implemented | clean release installation verified |
| Quality | Runtime dependency license policy | Implemented | isolated inventory; blocks selected strong-copyleft runtime deps |
| Security automation | Runtime pip-audit/Bandit/Gitleaks | Implemented | plus high-confidence secret patterns |
| Workflow security | Full SHA pins/least privilege/actionlint/yamllint/zizmor | Implemented | `pull_request_target` and `write-all` rejected |
| Container | Minimal multi-stage non-root image | Implemented | hardened read-only runtime compatibility checked |
| Container security | Trivy CVE gate + image CycloneDX SBOM | Implemented | fixed CRITICAL findings block |
| Supply chain | Multi-arch GHCR release | Implemented | amd64 + arm64, provenance/SBOM metadata |
| Supply chain | Release checksums/SBOMs/immutable digest | Implemented | independent Release Verification workflow |
| GitHub automation | PR policy and safe path labeling | Implemented | Conventional title + risk-sensitive evidence sections |
| GitHub automation | Dependabot Python/Actions/Docker | Implemented | grouped weekly Bangkok schedule |
| GitHub automation | Repository capability health report | Implemented | read-only; records unavailable/403 capabilities truthfully |
| GitHub security | CodeQL/Dependency Review | External gate | workflows prepared; private-repo plan/settings dependent |
| GitHub security | Secret scanning/push protection | External gate | repository/account capability |
| GitHub protection | `uat`/`production` environments | External gate | required reviewers/secrets must be configured in GitHub |
| GitHub protection | main ruleset/branch protection/merge queue | External gate | source workflows support `merge_group`; plan/settings dependent |
| Supply chain | GitHub artifact attestations | External gate | capability-gated for private repository |
| Production | Machine-readable readiness and canary plan | Implemented | non-executing; one-order/non-autonomous plan only |
| Production | Broker/legal/UAT/TLS/secrets/monitoring/DR/incident/rollback/capacity/time-sync/failover/retention/release evidence | External gate | source cannot self-certify operational facts |
