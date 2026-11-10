# ZKSATO Dashboard API Mapping

All frontend requests route through authenticated helpers [`getAuthHeaders()`](file:///home/cvsz/zksato/frontend/src/utils/api.ts#L28-L37) passing `X-API-Key`.

| Dashboard Feature | HTTP Method | Endpoint | Response Model | Error Handling |
|---|---|---|---|---|
| Engine Health & Mode | `GET` | `/health` | `HealthInfo` | Fallback to 'offline' on network failure |
| Operator Identity | `GET` | `/v1/auth/me` | `dict[str, str]` | Prompts login modal if 401 |
| Issue Session | `POST` | `/v1/auth/session` | `IssuedSession` | Displays auth rejection banner |
| Destroy Session | `DELETE` | `/v1/auth/session` | `dict[str, bool]` | Clears sessionStorage on teardown |
| Portfolio & P&L | `GET` | `/v1/portfolio` | `PortfolioSummary` | Zero-value safe defaults |
| Orders List | `GET` | `/v1/orders` | `list[Order]` | Shows empty state if empty |
| Cancel Open Orders | `POST` | `/v1/orders/cancel-all` | `dict[str, int]` | Toast notification on result |
| Executed Fills | `GET` | `/v1/fills` | `list[Fill]` | Shows formatted trade log |
| Trading Signals | `GET` | `/v1/signals` | `list[Signal]` | Displays strength percent badge |
| Alert Rules | `GET` | `/v1/alerts` | `list[Alert]` | Critical/Warning severity pills |
| Delete Alert | `DELETE` | `/v1/alerts/{id}` | `dict[str, bool]` | Refreshes alert table |
| Market Scanner | `GET` | `/v1/scanner` | `list[ScanResult]` | Directional signal formatting |
| Risk Evaluations | `GET` | `/v1/risk/evaluations` | `RiskEvaluations` | Authority limits display |
| Order Preflight | `POST` | `/v1/risk/preflight` | `RiskDecision` | Approved/Rejected reason breakdown |
| Audit Trail | `GET` | `/v1/audit?limit=15` | `list[AuditEvent]` | Immutable cryptographic chain |
| Environment Config | `GET`/`PUT` | `/v1/admin/env` | `dict[str, str]` | Restricted to `platform_admin` |
