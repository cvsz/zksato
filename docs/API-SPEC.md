# API specification

The deployed OpenAPI document at `/docs` on port `9569` is authoritative. This file summarizes v0.5 roles, endpoints, and safety boundaries.

## Authentication and sessions

When `ZKSATO_AUTH_REQUIRED=true`, versioned endpoints require an authorized API key/Bearer credential or valid signed session. Roles are `read_only`, `strategy_operator`, `order_approver`, `risk_admin`, `auditor`, and `platform_admin`.

- `POST /v1/auth/session` — exchange a machine credential for an expiring HttpOnly session and CSRF token
- `DELETE /v1/auth/session` — revoke the current session
- `GET /v1/auth/me` — current subject/role/auth method

Session-authenticated mutations require `X-CSRF-Token` when enabled. Secrets/broker credentials are never returned.

## Platform and health

- `GET /livez` — process liveness
- `GET /health` — non-throwing health summary
- `GET /readyz` — 503 unless persistence, coordination, reconciliation and audit-chain readiness pass
- `GET /metrics` — Prometheus exposition
- `GET /v1/config` — non-secret policy including paper execution/calendar settings
- `GET /v1/dashboard` — dashboard snapshot

Responses propagate a supplied `X-Request-ID` or return the generated correlation ID.

## Market/reference/scanning

- `GET /v1/market/session`
- `POST /v1/market/quote`
- `GET /v1/market/quotes`
- `GET /v1/market/history/{symbol}`
- `GET /v1/market/health/{symbol}`
- `POST /v1/market/demo/start|stop`
- `POST /v1/market/settrade/start|stop`
- `GET /v1/market/settrade/status`
- `GET /v1/reference/instruments`
- `GET /v1/scanner`

## Automation

- `GET /v1/bot`
- `POST /v1/bot/start`
- `POST /v1/bot/pause`
- `POST /v1/bot/resume`
- `POST /v1/bot/stop`
- `POST /v1/bot/tick`
- `GET /v1/signals`

Live mode rejects `auto_execute=true`; autonomous live execution is unavailable.

## TradingView webhooks and alerts

- `POST /v1/tradingview/webhook` — HMAC-SHA256 authenticated webhook endpoint supporting global and per-symbol secrets
- `POST /v1/tradingview/config` — Configure per-symbol webhook secrets
- `DELETE /v1/tradingview/config/{symbol}` — Delete per-symbol webhook secret
- `POST /v1/telegram/test` — Test Telegram notification channel

## Agent OS (Native Autonomous Intelligence)

- `GET /v1/agent-os/skills` — Enumerate all registered financial intelligence skills and parameter schemas
- `GET /v1/agent-os/subaccounts` — List active agent sub-accounts and collateral allocations
- `POST /v1/agent-os/subaccounts` — Create an isolated, zero-withdrawal agent sub-account
- `POST /v1/agent-os/execute` — Execute an Agent OS skill through the pre-trade `RiskEngine` boundary

## Equity risk and orders

- `POST /v1/risk/check` — explicit-context what-if only
- `POST /v1/risk/preflight` — derives trusted server/account/quote/reference context
- `POST /v1/orders`
- `GET /v1/orders?symbol=&status=&side=&limit=`
- `GET /v1/orders/{order_id}`
- `DELETE /v1/orders/{order_id}`
- `POST /v1/orders/cancel-open?symbol=`
- `POST /v1/reconcile`
- `GET /v1/portfolio`

The money-moving order endpoint ignores client-supplied `RiskContext` for execution and rebuilds it from trusted server state. Missing/stale data, reconciliation uncertainty, account policy failure, or configured limits fail closed.

`client_order_id` is the durable idempotency key. Ambiguous broker outcomes become `needs_reconciliation` and are not blindly retried. Cumulative broker fill snapshots are converted into incremental durable fills.

## Live approvals

- `POST /v1/live-approvals` — `risk_admin`; fresh preflight then short-lived exact-intent approval
- `GET /v1/live-approvals` — `risk_admin`

Approvals are single-use and can require a distinct creator/executor. Approval never bypasses a later risk check.

## Evidence and audit

- `GET /v1/order-events`
- `GET /v1/fills`
- `GET /v1/risk/evaluations`
- `GET /v1/account-snapshots`
- `GET /v1/audit`
- `GET /v1/audit/verify`
- `POST /v1/alerts`
- `GET /v1/alerts`
- `DELETE /v1/alerts/{alert_id}`

## Research

- `POST /v1/backtest`
- `POST /v1/research/bars`
- `GET /v1/research/bars/{symbol}`
- `POST /v1/research/strategies/{name}/{version}`
- `GET /v1/research/strategies`
- `GET /v1/research/runs`
- `POST /v1/research/replay/{symbol}`
- `POST /v1/research/walk-forward`
- `POST /v1/research/video-ea/plan`
- `POST /v1/research/video-ea/replay`
- `POST /v1/research/video-ea/parameter-sweep`
- `POST /v1/research/video-ea/rolling-walk-forward`
- `POST /v1/research/video-ea/monte-carlo`
- `POST /v1/research/video-ea/sensitivity`
- `POST /v1/research/video-ea/exposure-heatmap`
- `POST /v1/research/video-ea/lifecycle-metrics`
- `GET /v1/research/video-ea/state/{symbol}`
- `POST /v1/research/video-ea/arm`
- `POST /v1/research/video-ea/price/{symbol}`
- `POST /v1/research/video-ea/pause/{symbol}`
- `POST /v1/research/video-ea/resume/{symbol}`
- `POST /v1/research/video-ea/reset/{symbol}`
- `POST /v1/research/drift`
- `POST /v1/research/promotion`

Research endpoints have no broker submission authority. Video-EA operator controls require `paper` mode, persist only non-executable cycle snapshots, and are restricted to the strategy-operator role for mutations. Backtests model configured commission/slippage and expose closed-trade P&L, profit factor, fees, exposure, and buy-and-hold benchmark metrics. Sweep, rolling walk-forward, Monte Carlo, adverse-grid, cost-sensitivity, exposure-heatmap and lifecycle endpoints are deterministic research evidence only.

## Production readiness

- `POST /v1/production/readiness`
- `POST /v1/production/canary-plan`

These are evidence/reporting endpoints only; they do not submit orders or certify external broker/legal/deployment facts.

## TFEX

- `GET /v1/tfex/account`
- `GET /v1/tfex/portfolio`
- `GET /v1/tfex/orders`
- `GET /v1/tfex/contracts`
- `POST /v1/tfex/risk/check`
- `POST /v1/tfex/risk/preflight`
- `POST /v1/tfex/orders/uat` — sandbox/UAT-only

Production TFEX mutation is intentionally absent.

## Error and correlation semantics

HTTP 4xx represents validation/policy/risk conflicts; 5xx is reserved for server faults. Broker ambiguity retains auditable unresolved state. API keys, session material, Settrade App Secret/PIN, reusable authorization data, and configured secret-file contents must never be returned in API/audit output.
