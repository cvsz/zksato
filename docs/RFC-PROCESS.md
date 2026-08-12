# RFC process

Use an RFC for broad proposals that need discussion before an ADR or implementation.

## When
New execution model, major API/domain change, new persistence/broker architecture, major security/auth change, new deployment topology, or cross-cutting research/risk capability.

## States
Draft → Review → Accepted/Rejected/Superseded. Accepted architectural choices should be captured as ADRs when implementation direction becomes binding.

## Required content
Problem, goals/non-goals, proposal, alternatives, data/API changes, security/risk impact, operational impact, migration/rollout/rollback, testing/evidence, unresolved questions.

Start from `docs/templates/RFC.md` and keep implementation PRs linked to the decision record.
