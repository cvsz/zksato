# Traceability matrix

Use this matrix to connect requirements to implementation and evidence. Update rows when behavior materially changes.

| Requirement area | Primary implementation | Primary evidence |
|---|---|---|
| Market freshness/session/reference | `market_settrade.py`, `market_rules.py`, `risk.py` | market/risk tests, UAT evidence |
| Strategy/research | `strategy.py`, `indicators.py`, `research.py`, `backtest.py` | replay/backtest/walk-forward tests |
| Pre-trade risk | `risk.py`, `service.py` | risk property/unit tests, risk evaluations |
| Order execution/idempotency | `service.py`, `broker/`, `store.py`, `persistence.py` | order/idempotency tests, order events |
| Reconciliation | `reconcile.py`, `session_reconcile.py` | reconciliation/restart tests, broker UAT |
| Portfolio/fills | `portfolio.py`, fill ledger/store | fill-delta/accounting tests |
| Auth/approval | `auth.py`, `approvals.py`, `security.py` | auth/session/CSRF/approval tests |
| Audit | `store.py`, `persistence.py` | audit-chain tests |
| TFEX | `tfex.py` | TFEX unit tests + broker UAT certification |
| Operations | API health, observability, scripts, workflows | CI, DR, performance, release artifacts |
| Production readiness | `production.py` + workflow/runbooks | external readiness evidence |

For detailed P-level capability state, use `FEATURE-MATRIX.md` and `ROADMAP.md`.
