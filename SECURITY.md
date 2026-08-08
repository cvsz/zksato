# Security Policy

## Security model

zksato treats broker mutation as a privileged operation. The system is designed so that market analysis, strategy output, dashboard state and future AI components cannot bypass deterministic server-side risk and execution policy.

## Supported security posture

The current v0.2 release is intended for:

- local paper trading
- isolated development environments
- controlled Settrade UAT/sandbox validation

It is **not yet a hardened multi-user internet-facing production service**. Production deployment additionally requires authenticated RBAC, TLS, durable broker reconciliation, managed secrets, observability and disaster-recovery controls listed in `ROADMAP.md`.

## Live execution boundary

Live mode is fail-closed:

- live trading is disabled by default
- complete Settrade credentials are required server-side
- deterministic risk checks run before broker execution
- explicit live enablement is required
- a server-configured confirmation token is required for an explicit live order
- autonomous live execution is rejected even if a bot is configured for auto execution
- frontend state cannot override these controls

Do not weaken these conditions in a UI-only change.

## Secret handling

Never commit:

- Settrade App ID/App Secret
- account numbers
- PIN values
- live confirmation tokens
- webhook credentials
- broker session material

Use environment injection or a managed secret store. Restrict secret access to the execution service identity. Do not expose secrets through `/v1/config`, dashboard payloads, logs or audit messages.

## Network deployment

If exposing the application outside a trusted workstation/network, place it behind an authenticated TLS reverse proxy. Until native RBAC is implemented, do not expose mutation endpoints directly to the public internet.

Recommended production layers include:

- TLS 1.2+
- SSO/OIDC or equivalent operator authentication
- role-based authorization
- CSRF protection for cookie-authenticated deployments
- network allow-lists where practical
- request rate limits
- managed firewall/WAF policy

## Supply chain

Before production release:

- pin and review dependency versions
- scan dependencies and container images
- generate an SBOM
- review GitHub Actions permissions
- use protected production environments
- keep production credentials out of pull-request workflows

## Vulnerability reporting

Do not disclose live broker credentials, account information or exploitable production details in a public issue. Use a private security-reporting channel configured by the repository owner.

A useful report should include:

- affected commit/version
- reproduction steps
- expected and actual behavior
- potential impact
- whether the issue can cross the paper/UAT/live boundary
- relevant sanitized logs

## High-priority vulnerability classes

Treat the following as critical or high severity:

- any bypass of `RiskEngine` or `TradingService`
- any path allowing autonomous live broker mutation
- secret disclosure
- confirmation-token bypass
- cross-account order routing
- duplicate order execution after retries/restarts
- order-state desynchronization that can create unintended exposure
- unauthenticated remote mutation in a production deployment

## Operational response

If an execution-boundary vulnerability is suspected:

1. stop automation
2. activate the application kill switch
3. review/cancel open broker orders using the approved broker interface
4. remove or rotate exposed credentials
5. preserve logs and audit data
6. reproduce only in paper/UAT
7. patch and rerun CI/UAT before restoring service

The application kill switch blocks new submissions; it does not guarantee cancellation of orders already accepted by the broker.
