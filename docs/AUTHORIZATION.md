# Authentication and authorization

## Target roles
- `viewer`: read-only market/portfolio/audit.
- `strategy_operator`: start/stop paper/UAT strategies and manage non-sensitive parameters.
- `order_approver`: approve explicit broker mutations within policy.
- `risk_admin`: change risk policy/kill switch with audit.
- `platform_admin`: deployment/integration administration; cannot bypass risk checks.
- `auditor`: read/export immutable audit evidence.

## Requirements
Strong authentication, secure HTTP-only sessions or equivalent, CSRF protection for browser mutations, RBAC checked server-side, re-auth/step-up for sensitive live actions, session expiry/revocation, rate limiting, full audit.

## Secrets
Live confirmation authority must not be delivered as a static frontend secret. Move from shared token toward authenticated short-lived approval records/nonces tied to exact order intent.
