# API specification

Current FastAPI endpoints remain discoverable at `/docs` on port `9569`. This document defines target conventions.

## Conventions
- `/v1/` versioned HTTP API.
- JSON responses with stable typed schemas.
- UTC ISO-8601 timestamps.
- Correlation/request ID on mutating operations.
- Idempotency key required for external money-moving order submission.
- Auth/RBAC required before non-local exposed deployment.
- Never return credentials/PINs/secrets.

## Target groups
- `/v1/health`, `/v1/config`, `/v1/status`
- `/v1/market/*` quotes/history/subscriptions status
- `/v1/strategies/*`, `/v1/backtests/*`
- `/v1/signals/*`
- `/v1/risk/*`
- `/v1/orders/*`, `/v1/fills/*`
- `/v1/portfolio/*`, `/v1/accounts/*`
- `/v1/bot/*`
- `/v1/alerts/*`, `/v1/audit/*`
- `/v1/admin/*` for privileged configuration

## Error model
Return machine-readable code, human message, correlation ID, retryability classification, and sanitized broker details when safe. Ambiguous broker outcomes must not be reported as confirmed failure.
