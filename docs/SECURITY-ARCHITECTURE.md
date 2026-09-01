# Security architecture

## Trust zones
Browser is untrusted for policy; FastAPI/auth layer validates identity/authorization; RiskEngine and TradingService are trusted policy boundaries; broker adapter holds external mutation capability; secret store is separate privileged infrastructure.

## Live approval target
Replace shared static confirmation tokens with short-lived, single-use, server-stored approval records bound to exact account/order intent, authenticated operator, expiry, and correlation ID.

## Defense in depth
TLS/reverse proxy, secure session cookies (secure flag in prod/uat), CSRF, strict CORS, rate limiting, input schemas, RBAC, audit, secret manager, dependency/container scanning, network egress controls where practical.

## Session management
- HMAC-signed HttpOnly sessions with automatic pruning of expired sessions
- Session revocation set bounded to prevent unbounded memory growth
- Session cookie `secure` flag enabled in production and UAT environments

## Environment file validation
Deployment scripts validate environment files before sourcing:
- Permission checks (recommends 600 or 400)
- Injection pattern detection (rejects `;`, `$()`, backticks, `&&`, `||`, pipes)
- Required secrets validation

## Key rule
No frontend, strategy, plugin, AI agent, or admin convenience endpoint may directly invoke live broker mutation outside TradingService + RiskEngine + authorization.
