# API specification

The deployed OpenAPI document at `/docs` on port `9569` is authoritative. This file summarizes the stable groups, roles, and trust boundaries for v0.4.

## Authentication and sessions

When `ZKSATO_AUTH_REQUIRED=true`, versioned endpoints require an authorized API key/Bearer credential or a valid signed session. Roles are `read_only`, `strategy_operator`, `order_approver`, `risk_admin`, `auditor`, and `platform_admin`.

- `POST /v1/auth/session` — exchange a valid machine credential for an expiring HttpOnly session; response contains the CSRF token
- `DELETE /v1/auth/session` — revoke the current session in the running process and clear its cookie
- `GET /v1/auth/me` — current subject, role, and auth method

Session-authenticated mutating requests require `X-CSRF-Token` when CSRF protection is enabled. Secrets and broker credentials are never returned by the API.

## Platform

- `GET /health` — persistence, Redis coordination, reconciliation, provider configuration, and audit-chain health
- `GET /metrics` — Prometheus exposition
- `GET /v1/config` — non-secret runtime policy
- `GET /v1/dashboard` — dashboard snapshot

## Market/reference/scanning

- `POST /v1/market/quote`
- `GET /v1/market/quotes`
- `GET /v1/market/history/{symbol}`
- `GET /v1/market/health/{symbol}`
- `POST /v1/market/demo/start|stop`
- `POST /v1/market/settrade/start|stop`
- `GET /v1/market/settrade/status`
- `GET /v1/reference/instruments`
- `GET /v1/scanner`

The Settrade status includes connection state, feed freshness, reconnect count, sequence-gap count, out-of-order count, and last error. Trusted instrument metadata can drive sector, tick-size, and price-band controls.

## Automation

- `GET /v1/bot`
- `POST /v1/bot/start|stop|tick`
- `GET /v1/signals`

Autonomous production live execution remains disabled by server policy.

## Equity risk and controlled orders

- `POST /v1/risk/check` — explicit-context what-if evaluation; never authorizes execution
- `POST /v1/risk/preflight` — derives account/portfolio/order/quote/reference context on the server
- `POST /v1/orders`
- `GET /v1/orders`
- `DELETE /v1/orders/{order_id}`
- `POST /v1/reconcile`
- `GET /v1/portfolio`

The order endpoint does not trust client-supplied `RiskContext`. It reconstructs execution context from server state and trusted market/reference data before evaluating `RiskEngine`. Missing/stale data, reconciliation uncertainty, invalid account policy, or configured risk-limit violations fail closed.

`client_order_id` is the durable idempotency key. Ambiguous broker outcomes use `needs_reconciliation`; they are not blindly retried.

## Privileged approval records

- `POST /v1/live-approvals` — `risk_admin`; preflights and creates a short-lived fingerprint for an exact `OrderIntent`
- `GET /v1/live-approvals` — `risk_admin`

Approvals are single-use and can require a distinct creator and executor. A fresh trusted risk evaluation is performed later, so approval does not freeze or bypass subsequent risk conditions.

## Durable evidence and audit

- `GET /v1/order-events` — durable order lifecycle events
- `GET /v1/fills` — durable fill records
- `GET /v1/risk/evaluations` — durable risk decisions and inputs
- `GET /v1/audit` — redacted audit events
- `GET /v1/audit/verify` — verify the in-memory/loaded hash chain
- `POST /v1/alerts`
- `GET /v1/alerts`
- `DELETE /v1/alerts/{alert_id}`

## Research

- `POST /v1/backtest`
- `POST /v1/research/bars`
- `POST /v1/research/replay/{symbol}`
- `POST /v1/research/walk-forward`
- `POST /v1/research/promotion`

Research endpoints have no broker-submission authority. Replay/walk-forward can honor configured market sessions. Backtesting uses commission/slippage inputs and the shared deterministic strategy engine.

## Production readiness

- `POST /v1/production/readiness` — combines runtime checks with operator-supplied external evidence
- `POST /v1/production/canary-plan` — produces a non-executing readiness plan only

These endpoints cannot certify broker/legal/deployment facts and do not submit orders.

## TFEX

- `GET /v1/tfex/account`
- `GET /v1/tfex/portfolio`
- `GET /v1/tfex/orders`
- `GET /v1/tfex/contracts`
- `POST /v1/tfex/risk/check` — explicit-context what-if evaluation
- `POST /v1/tfex/risk/preflight` — derives broker portfolio/margin, reference metadata, and market-data freshness
- `POST /v1/tfex/orders/uat` — sandbox/UAT-only endpoint

TFEX uses a dedicated domain with contract multiplier, tick, expiry, settlement, margin, and position semantics. Production TFEX mutation is intentionally unavailable pending external UAT certification.

## Error and correlation semantics

HTTP 4xx represents validation/policy/risk conflicts; 5xx is reserved for server faults. Broker ambiguity preserves an auditable reconciliation state. Responses and audit records must not expose API keys, session material, App Secret, PIN, or reusable authorization data.

Mutating workflows should propagate `X-Request-ID` for correlation; server-generated correlation IDs are also attached to request context and observability records.
