# Documentation standard

## Goals
Documentation must describe implemented behavior, intended controls, known limitations, and external gates without overstating completion.

## Required qualities
- revision-relevant and technically precise;
- distinguish source-controlled capability from external deployment/broker evidence;
- include failure behavior for operational/trading-sensitive features;
- use relative repository links where practical;
- never include credentials/account secrets;
- update related API/database/domain/feature/runbook/ADR material in the same PR.

## Document lifecycle
Draft proposals use RFCs. Accepted architecture uses ADRs. Operational procedures use runbooks. Incidents use incident/postmortem records. Evidence-heavy changes use templates under `docs/templates/`.

## Ownership
CODEOWNERS/relevant domain maintainers review high-risk documentation. `docs/INDEX.md` is the canonical human navigation page.
