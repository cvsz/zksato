# Feature matrix

Status values: **Implemented**, **Partial**, **Planned**, **Deployment-dependent**.

| Area | Capability | Status | Notes |
|---|---|---:|---|
| API | FastAPI control plane on 9569 | Implemented | `/docs`, `/health`, trading endpoints |
| Dashboard | Single-node operator dashboard | Implemented | Market, portfolio, orders, signals, audit |
| Paper | Immediate paper fill simulator | Implemented | Market/marketable-limit behavior |
| Portfolio | Paper cash/position/P&L | Implemented | Process-local state |
| Strategy | EMA/RSI/breakout | Implemented | Deterministic |
| Backtest | Shared-strategy backtester | Implemented | Needs richer fees/slippage/walk-forward |
| Risk | Core pre-trade controls | Implemented | Needs exposure/sector/session/stale-feed expansion |
| Automation | Paper/UAT bot lifecycle | Implemented | Live autonomous execution intentionally forbidden |
| Alerts | Price alerts/webhook notification | Implemented | Generic webhook |
| Settrade | Equity adapter | Partial | Requires SDK/UAT certification and deeper reconciliation |
| Market data | Synthetic demo feed | Implemented | Never live data |
| Market data | Native Settrade realtime feed | Planned | Reconnect/staleness/replay required |
| Persistence | PostgreSQL durable order state | Planned | Compose service exists; not system of record yet |
| Coordination | Redis locks/cache | Planned | Compose service exists |
| Reconciliation | Durable broker order/deal reconciliation | Planned | P0 before live-scale use |
| Auth | Operator authentication/RBAC | Planned | Required before exposed deployment |
| TFEX | Dedicated execution/margin domain | Planned | Must not reuse equity assumptions |
| Observability | Prometheus/OTel/Grafana/Loki | Planned | Structured correlation required |
| DR | Backup/restore/recovery | Planned | Requires durable DB first |
| Security | Server-side secrets/live confirmation boundary | Implemented | Managed secret store still planned |
| AI | Read-only research/explanation boundary | Planned | Never direct broker authority |

Update this file in every PR that materially changes capability status.
