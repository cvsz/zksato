# Security Policy

## Security model
zksato treats broker mutation, credentials, approvals, account state, and production readiness evidence as privileged assets. Market analysis, strategy output, dashboard state, and AI/agent components cannot bypass deterministic server-side risk and execution policy.

## Supported posture
The repository supports local paper development and controlled broker UAT workflows. Production readiness is intentionally fail-closed and requires source controls plus external evidence defined in `docs/PRODUCTION-READINESS.md` and `docs/PRODUCTION-CHECKLIST.md`.

## Execution boundary
- `paper` is the default mode.
- Autonomous live-money execution is forbidden.
- Live equity mutation requires trusted server-side risk, configured credentials, reconciliation readiness, and explicit one-time operator authorization.
- Broker reconciliation freshness is process/session-local and must be re-established after restart.
- TFEX production mutation remains disabled/UAT-only until separately certified.
- Frontend, strategy, agent, or LLM state cannot override these controls.

## Authentication and authorization
The application supports API-key RBAC and signed HttpOnly sessions with CSRF controls. Production deployments must configure authentication, strong session signing material, trusted hosts/origins, TLS termination, rate limiting, account allow-lists, and least-privilege operator roles.

## Secrets
Never commit or persist in logs/UI/audit messages:
- Settrade App Secret, PIN, access/session tokens;
- reusable API keys or live confirmation material;
- webhook credentials or signed callback secrets;
- cloud/database credentials;
- private account data not required for the evidence record.

Use environment injection or mounted/managed secrets. Rotate exposed material and preserve only sanitized forensic evidence.

## Supply chain
Required controls include immutable Action SHA pins, dependency auditing, SAST, secret scanning, container scanning, SBOM generation, least-privilege workflow permissions, and protected deployment environments where the GitHub plan supports them. See `docs/SUPPLY-CHAIN.md`.

## Vulnerability reporting
Do not post exploitable details or credentials in a normal issue. Use GitHub private vulnerability reporting/security-advisory capability when available, or contact the repository owner through an agreed private channel. A useful report includes affected revision, reproduction in paper/UAT, impact, sanitized evidence, and whether execution/risk/auth boundaries can be crossed.

## Priority vulnerability classes
Treat as critical/high until triaged:
- `RiskEngine`/`TradingService` bypass;
- autonomous live execution path;
- credential, PIN, session, approval, or account-data disclosure;
- cross-account routing;
- duplicate order execution or broken idempotency;
- stale reconciliation readiness after restart;
- order-state divergence that can create unintended exposure;
- unauthenticated/unauthorized mutation;
- migration or restore behavior that corrupts durable order/fill/risk/audit state.

## Response
1. stop automation;
2. activate the application kill switch;
3. review/cancel open broker orders using the approved broker interface;
4. isolate affected services and rotate exposed credentials;
5. preserve sanitized logs/audit/database evidence;
6. reproduce only in paper/UAT;
7. patch, validate, and complete security review;
8. restore service only through the approved rollout process.

The application kill switch blocks new submissions; it does not guarantee cancellation of broker-accepted orders.
