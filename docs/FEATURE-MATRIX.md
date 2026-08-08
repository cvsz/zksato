# Feature matrix

Status values: **Implemented**, **Partial**, **Planned**, **Deployment-dependent**.

| Area | Capability | Status | Notes |
|---|---|---:|---|
| API | FastAPI control plane on 9569 | Implemented | OpenAPI, health, versioned control endpoints |
| Dashboard | Single-node operator dashboard | Implemented | Market, portfolio, orders, signals, audit |
| Paper | Fill simulator and protective exits | Implemented | Paper account can persist through SQL store |
| Portfolio | Paper cash/position/P&L recovery | Implemented | SQL `runtime_state` when DB configured |
| Strategy | EMA/RSI/breakout | Implemented | Deterministic shared engine |
| Indicators | SMA/EMA/RSI/ATR/ADX/Bollinger/VWAP | Implemented | Deterministic calculations |
| Backtest | Commission/slippage-aware backtester | Implemented | Walk-forward/replay promotion reports still planned |
| Risk | Equity pre-trade controls | Implemented | Position/risk/loss/drawdown/open-order/notional/exposure/stale/spread guards |
| Automation | Paper/UAT bot lifecycle | Implemented | Autonomous live execution intentionally forbidden |
| Alerts | Durable webhook outbox | Implemented | Retries pending SQL outbox entries |
| Settrade | Equity adapter | Partial | Code integrated; installed SDK/account still requires UAT certification |
| Market data | Synthetic demo feed | Implemented | Paper-only, never actual SET data |
| Market data | Settrade realtime price/bid-offer bridge | Partial | Native subscriptions implemented; long-running reconnect behavior needs UAT evidence |
| Scanner | Momentum/volume quote ranking | Implemented | Deterministic API scanner |
| Persistence | PostgreSQL/SQLAlchemy durable operational state | Implemented | Orders/quotes/signals/audit/alerts/idempotency/outbox/paper account |
| Migrations | Versioned PostgreSQL baseline | Implemented | `migrations/0001_core.sql`; future changes append migrations |
| Coordination | Redis locks/cache | Planned | Compose service exists; no correctness dependency yet |
| Reconciliation | Broker order reconciliation worker | Implemented | Ambiguous outcomes fail into reconciliation; broker snapshot semantics require UAT evidence |
| Auth | API-key authentication/RBAC | Implemented | Exposed production should use external identity/secret management where available |
| Approval | One-time intent-bound live approval | Implemented | Optional four-eyes distinct risk-admin/order-approver flow |
| HTTP security | Rate limit/CORS/trusted hosts/security headers | Implemented | Rate limiter is per process, not distributed |
| TFEX | Dedicated domain/risk/read APIs | Implemented | Separated from equity assumptions |
| TFEX | Order mutation | Partial | UAT-only gateway; exact installed SDK lifecycle must be certified before expansion |
| Observability | Prometheus metrics | Implemented | Full OTel/Grafana/Loki deployment remains deployment-dependent |
| DR | Backup/restore/recovery exercises | Deployment-dependent | Requires operator infrastructure and drills |
| Security | Server-side secrets and live execution boundary | Implemented | Managed KMS/Vault integration remains deployment-dependent |
| AI | Read-only research/explanation boundary | Planned | Never direct broker authority |
| Live rollout | Manual-confirmation canary | Deployment-dependent | Requires broker permission, UAT evidence and operator decision |

Update this file in every PR that materially changes capability status.
