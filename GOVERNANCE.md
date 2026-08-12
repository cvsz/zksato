# Governance

## Decision model
Routine implementation decisions are made through review. Cross-cutting, difficult-to-reverse, security-sensitive, data-model, or execution-policy changes require an ADR under `docs/adr/`; broad proposals may start as an RFC using `docs/templates/RFC.md`.

## Non-waivable invariant
No maintainer, review, feature flag, UI, strategy, agent, or LLM may grant unrestricted autonomous live broker mutation. Live equity execution remains a deterministic server-side risk and explicit-operator operation. TFEX production mutation remains disabled until separately certified and governed.

## Required ADR topics
- live execution/trust-boundary policy;
- persistence/system-of-record changes;
- order idempotency and reconciliation;
- market-data/reference-data architecture;
- authentication/authorization/session model;
- TFEX execution/margin semantics;
- event/outbox architecture;
- externally visible API compatibility changes;
- deployment architecture that changes failure domains.

## Change authority
- Low-risk docs/tests: normal review.
- Product/runtime changes: owner review plus required CI.
- Risk/security/execution/migration changes: explicit evidence sections and CODEOWNERS review.
- Release preparation: source checks, artifacts, changelog/release notes, rollback path.
- UAT/production promotion: separate environment authorization and evidence; repository source alone cannot approve it.

## Evidence policy
Facts about broker permissions, Settrade UAT, TLS, secrets management, backups, monitoring, legal approval, production capacity, and live canaries must be backed by environment-specific evidence. Do not convert intended configuration into a completion claim.

## Emergency changes
Use the hotfix PR template. Preserve auditability, state the incident/change reference, minimize scope, and perform a post-change review/postmortem when the emergency is over.
