# API Security Review

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Authentication & Authorization

- **Principal Resolution**: All secured endpoints require authentication via Bearer API keys (`Authorization: Bearer <token>`).
- **Role Hierarchy**:
  - `ReadPrincipal`: Read-only queries (`GET /v1/portfolio`, `GET /v1/orders`, `GET /v1/quotes`).
  - `OrderPrincipal`: Order submission and cancellation (`POST /v1/orders`, `POST /v1/cancel`).
  - `StrategyPrincipal`: Automated agent order execution and advisory intake (`POST /v1/integrations/ztrader/*`).
  - `AdminPrincipal`: Configuration, kill switches, approvals, and system state modification.

## 2. OWASP ASVS Defenses
- **Input Validation**: Strict Pydantic models for all incoming JSON payloads. Extra fields are rejected.
- **Sensitive Data Redaction**: Log redaction via `redact_sensitive` masks PINs, broker keys, and tokens.
- **Security Headers**: Frontend Next.js configuration sets `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy`, and `Strict-Transport-Security`.
- **CORS**: Scoped explicitly in API middleware to authorized origins; wildcard origins in live/authenticated modes are rejected.
