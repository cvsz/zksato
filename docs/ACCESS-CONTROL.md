# Access control

## Application roles
- `read_only`: read permitted resources.
- `strategy_operator`: research/strategy operations plus read.
- `order_approver`: controlled order approval/operations plus lower grants.
- `risk_admin`: risk administration plus lower grants.
- `auditor`: evidence-oriented read access.
- `platform_admin`: administrative superset.

Exact grants are implemented in `auth.py`; implementation is authoritative.

## Principles
Least privilege, separate duties for high-risk approval where configured, short-lived sessions, CSRF for unsafe cookie-authenticated methods, account allow-lists, server-side authorization, and no browser-held broker secrets.

## Production
Use unique credentials per actor/service, managed secret rotation, TLS, trusted origins/hosts, environment protection, and periodic access review. Remove departed/unused credentials promptly.

## GitHub
CODEOWNERS and repository roles are separate controls. Production environment secrets/reviewers and rulesets are external GitHub configuration and must be audited separately.
