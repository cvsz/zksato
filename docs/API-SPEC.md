# API specification

The deployed OpenAPI document at `/docs` on port `9569` is authoritative. This file summarizes the stable groups and trust boundaries.

## Authentication

When `ZKSATO_AUTH_REQUIRED=true`, versioned endpoints require `X-API-Key` or `Authorization: Bearer <key>` according to role grants. Secrets are never returned by the API.

Roles: `read_only`, `strategy_operator`, `order_approver`, `risk_admin`, `auditor`, `platform_admin`.

## Platform

- `GET /health` — liveness/persistence and provider configuration state
- `GET /metrics` — Prometheus exposition, read role when auth is enabled
- `GET /v1/auth/me` — current principal/role
- `GET /v1/config` — non-secret runtime policy
- `GET /v1/dashboard` — dashboard snapshot

## Market and scanning

- `POST /v1/market/quote`
- `GET /v1/market/quotes`
- `GET /v1/market/history/{symbol}`
- `GET /v1/market/health/{symbol}`
- `POST /v1/market/demo/start|stop`
- `POST /v1/market/settrade/start|stop`
- `GET /v1/scanner`

## Automation/research

- `GET /v1/bot`
- `POST /v1/bot/start|stop|tick`
- `POST /v1/backtest`
- `GET /v1/signals`

## Equity risk/execution

- `POST /v1/risk/check`
- `POST /v1/orders`
- `GET /v1/orders`
- `DELETE /v1/orders/{order_id}`
- `POST /v1/reconcile`
- `GET /v1/portfolio`

`client_order_id` is the durable idempotency key. An ambiguous broker response is represented as `needs_reconciliation`, not as confirmed failure.

## Live approval

- `POST /v1/live-approvals` — `risk_admin`; creates a short-lived approval fingerprint for the exact `OrderIntent`
- `GET /v1/live-approvals` — `risk_admin`
- `POST /v1/orders` in live mode — `order_approver`; must include `X-Live-Approval-Id` when confirmation is required

Approvals are single-use and may require the approval creator and executor to be distinct principals.

## TFEX

- `GET /v1/tfex/account`
- `GET /v1/tfex/portfolio`
- `GET /v1/tfex/orders`
- `POST /v1/tfex/risk/check`
- `POST /v1/tfex/orders/uat` — sandbox/UAT only, never a live endpoint

## Alerts/audit

- `POST /v1/alerts`
- `GET /v1/alerts`
- `DELETE /v1/alerts/{alert_id}`
- `GET /v1/audit`

## Error semantics

Use HTTP 4xx for validation/policy/risk conflicts and 5xx only for server faults. Broker ambiguity must preserve an auditable reconciliation state. Error responses and audit records must never include API secrets, PINs or reusable authorization material.
