# Governance

## Decision model
Routine implementation decisions are made through code review. Cross-cutting, irreversible, security-sensitive, or execution-policy changes require an ADR under `docs/adr/`.

## Required ADR topics
- Live execution policy and trust boundary
- Persistence/system-of-record changes
- Order idempotency/reconciliation model
- Market-data architecture
- Authentication/authorization model
- TFEX execution and margin model
- Event/outbox architecture

## Release authority
A release may be promoted only when CI is green, required migrations/runbooks exist, known critical risks are documented, and production-sensitive changes have an explicit rollback path.

## Live trading
No governance process may waive the repository rule that autonomous agents/LLMs cannot directly obtain unrestricted live broker mutation authority.
