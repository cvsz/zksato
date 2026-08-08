# Feature matrix

Status values: **Implemented**, **Partial**, **External-evidence**.

| Area | Capability | Status | Notes |
|---|---|---:|---|
| API | FastAPI control plane on 9569 | Implemented | OpenAPI, health, versioned control endpoints |
| Dashboard | Operator dashboard | Implemented | Market, portfolio, orders, signals, audit and controls |
| Paper | Fill simulator/protective exits/recovery | Implemented | Durable paper account when SQL configured |
| Persistence | PostgreSQL durable trading state | Implemented | Orders/events/fills/risk/account snapshots/bars/signals/audit/outbox/idempotency |
| Migrations | Versioned PostgreSQL migrations | Implemented | `0001_core.sql`, `0002_priority_state.sql` |
| Coordination | Redis distributed locks/rate-limit coordination | Implemented | PostgreSQL remains trading correctness boundary |
| Reconciliation | Broker order/fill convergence gate | Implemented | Ambiguous outcomes block broker execution until converged |
| Session reconciliation | Durable fills vs broker positions | Implemented | Independent end-of-session comparison service |
| Market data | Synthetic paper feed | Implemented | Never presented as real SET data |
| Market data | Settrade realtime supervisor | Implemented | Reconnect/backoff, freshness, gap/out-of-order diagnostics |
| Settrade | Equity account/order adapter | Partial | Source integrated; actual account/SDK behavior requires UAT evidence |
| Reference data | Instrument tick/band/sector registry | Implemented | Operator/trusted JSON reference boundary; strict mode available |
| Risk | Trusted server-derived equity pre-trade context | Implemented | Client-provided risk context is not trusted for order execution |
| Risk | Position/notional/loss/drawdown/spread/open-order controls | Implemented | Deterministic fail-closed checks |
| Risk | Gross/net/symbol/sector/session/tick/band/account controls | Implemented | Configurable server policy |
| Automation | Paper/UAT bot lifecycle | Implemented | Autonomous live execution intentionally forbidden |
| Strategy | EMA/RSI/breakout | Implemented | Shared deterministic engine |
| Indicators | SMA/EMA/RSI/ATR/ADX/Bollinger/VWAP | Implemented | Deterministic calculations |
| Scanner | Momentum/volume quote ranking | Implemented | Deterministic API scanner |
| Research | Durable historical OHLCV/replay | Implemented | Session-aware when session enforcement enabled |
| Research | Commission/slippage backtest | Implemented | Shared strategy engine |
| Research | Walk-forward/OOS reporting | Implemented | Promotion thresholds configurable |
| Research | Strategy/version registry and drift primitive | Implemented | Durable version/run persistence |
| Research | Research→paper→UAT→manual-live gates | Implemented | No direct broker authority |
| Auth | API-key RBAC | Implemented | Reader/strategy/order/risk/auditor/admin separation |
| Sessions | Signed expiring HttpOnly session + CSRF | Implemented | API keys remain available for machine clients |
| HTTP security | CORS/trusted hosts/CSP/HSTS/rate limits | Implemented | Redis coordinates rate limits when configured |
| Secrets | Secret-file loading and rotation procedure | Implemented | Managed KMS/Vault deployment remains environment-specific |
| Approval | One-time intent-bound live approval | Implemented | Optional four-eyes distinct approver/executor |
| Audit | Tamper-evident chain + redaction | Implemented | Hash-linked events and sensitive-output redaction |
| Alerts | Durable webhook outbox | Implemented | Retry dispatcher backed by durable outbox |
| TFEX | Dedicated domain/risk/read APIs | Implemented | Separated from equity assumptions |
| TFEX | Contract/series/expiry/tick/settlement model | Implemented | Trusted metadata registry |
| TFEX | Order mutation | Partial | UAT-only by design; live mutation not enabled |
| Observability | Prometheus metrics/JSON correlation logs | Implemented | Optional OTel traces |
| Observability | Prometheus alert/SLO config | Implemented | Production scrape/delivery requires deployment evidence |
| DR | Backup/restore scripts and runbook | Implemented | Actual restore drill/RPO/RTO requires deployment evidence |
| Load | Bounded load probe | Implemented | Production capacity evidence remains environment-specific |
| UAT | Non-mutating certification probe/runbook | Implemented | Broker-side outcomes require actual UAT account |
| Production | Readiness report and one-order canary plan | Implemented | Cannot self-certify external evidence |
| Production | Broker/legal/UAT/TLS/KMS/monitoring/DR evidence | External-evidence | Must be supplied by the real deployment/operator |
| AI | Research/explanation boundary | Implemented | AI never owns broker execution authority |
| Live execution | Autonomous live-money trading | External-evidence | Deliberately forbidden, not a completion target |

Update this file in every PR that materially changes capability status.
