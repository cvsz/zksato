# P0-P6 production completion execution plan

## Completion rule

A priority is **source-complete** when repository-controlled capabilities are implemented, guarded, documented, and covered by CI or an executable verification probe. A priority is **externally complete** only when evidence from the real broker/account/deployment exists. Source code must not fabricate broker, legal, TLS, secret-management, monitoring, recovery, capacity, or rollout evidence.

| Priority | Source status | External status | Boundary |
|---|---|---|---|
| P0 Durable correctness | Complete | N/A | PostgreSQL state, migrations, idempotency, events/fills, reconciliation, Redis coordination |
| P1 Trusted market/risk | Complete | UAT pending | realtime supervision/reference data/risk code complete; broker behavior needs UAT evidence |
| P2 Security/operator | Complete | deployment pending | RBAC/sessions/CSRF/redaction/audit complete; managed identity/secrets are deployment-specific |
| P3 TFEX | Complete for UAT | certification pending | domain/reference/risk/UAT boundary complete; production mutation remains disabled |
| P4 Observability/resilience | Complete | drills pending | metrics/logs/traces/SLO/alerts/backup/load tooling complete; measured evidence requires deployment |
| P5 Strategy research | Complete | strategy evidence pending | OHLCV/replay/backtest/walk-forward/version/promotion pipeline complete |
| P6 Controlled rollout | Complete control plane | approvals/evidence pending | readiness and reconciliation gates complete; external evidence is still required |

## P0 — Durable correctness

Implemented: PostgreSQL records for orders, order events, fills, risk evaluations, account snapshots, quotes, bars, signals, alerts, audit, idempotency, runtime state, and outbox; lexically ordered migrations; restart-safe client-order idempotency; ambiguous broker outcome classification without blind retry; reconciliation that keeps broker-facing operation closed until unresolved outcomes converge; durable fill capture; independent session position reconciliation; optional Redis distributed coordination; and restart/recovery/idempotency/reconciliation tests.

## P1 — Trusted market data and risk

Implemented: supervised Settrade realtime bridge with reconnect backoff; feed freshness, sequence-gap, and out-of-order diagnostics; server-derived portfolio/account/quote risk context; gross/net/symbol/sector exposure controls; open-order, daily-order, loss, drawdown, notional, and spread controls; optional market-session enforcement; trusted instrument metadata for tick size, price bands, and sectors; account allow-list; and intent-bound approval records.

External gate: validate the installed SDK and authorized UAT account across normal and failure scenarios described in `docs/UAT-CERTIFICATION.md`.

## P2 — Security and operator controls

Implemented: role-separated API-key RBAC; HMAC-signed expiring HttpOnly sessions and CSRF validation; CORS/trusted-host/CSP/HSTS headers; Redis-backed rate-limit coordination when configured; supported secret-file mounts and rotation runbook; hash-linked audit records and output redaction; and separated privileged roles.

External gate: production identity, managed secret backend, and organizational access review are deployment choices that require operator evidence.

## P3 — TFEX

Implemented: dedicated LONG/SHORT plus OPEN/CLOSE/AUTO domain; contract metadata covering series, multiplier, tick, expiry, and settlement; contract-count, margin, stale-data, tick, and expiry-window controls; account/portfolio/order reads; settlement P&L helper; and UAT-only mutation boundary.

External gate: certify response mappings, margin semantics, and installed-SDK behavior in the authorized UAT environment. Production TFEX mutation remains disabled until that certification exists.

## P4 — Observability, resilience, and recovery

Implemented: Prometheus metrics for HTTP, order/risk, reconciliation, feed freshness, outbox, and coordination; correlation context; JSON logs; optional OpenTelemetry traces; SLO definitions; Prometheus scrape and alert rules; PostgreSQL backup/restore scripts; disaster-recovery runbook; bounded HTTP load probe; and CI compile/dependency/migration/lint/test/Compose validation.

External gate: run recovery, outage, and capacity exercises in the target environment and retain measured evidence.

## P5 — Strategy research

Implemented: durable OHLCV bars; deterministic replay; shared strategy engine; commission and slippage modeling; market-session-aware replay/walk-forward when enabled; train/out-of-sample reporting; durable strategy/version/run records with configuration hash; drift primitive; and staged promotion evidence gates.

Strategy performance is not a source-code completion claim; advancement requires measured evidence from the applicable environment.

## P6 — Controlled production readiness

Implemented control-plane work: machine-readable readiness checks combining runtime controls with external evidence; a non-executing manual-canary planning object; independent durable-fill versus broker-position session reconciliation; UAT verification probe; and production-readiness, secrets, SLO, and DR runbooks.

External gates remain broker permission, legal/operational review, UAT certification, TLS, managed secrets, backup/restore evidence, monitoring evidence, and explicit operator authorization. These are recorded as evidence rather than marked complete by code.

## Permanent invariant

Autonomous live-money execution is forbidden. Completing P0-P6 does not remove that boundary. AI and strategy components may research, explain, and operate in non-production environments, but they do not independently authorize production broker actions.
