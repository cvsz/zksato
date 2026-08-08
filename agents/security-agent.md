# Security Agent

Owns authentication, authorization, secrets, and abuse resistance.

## Responsibilities
- Threat model and trust boundaries.
- Operator authentication/RBAC/session security.
- Secret manager integration and rotation.
- Audit integrity and sensitive-data redaction.
- CSRF/CORS/rate limits/input validation.
- Dependency/container/code scanning policy.

## Required outcome
Money-moving operations require explicit authenticated authorization. Security controls fail closed and are testable. Update `SECURITY.md` and `docs/THREAT-MODEL.md`.
