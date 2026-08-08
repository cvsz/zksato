# ADR-0007: Authenticated intent-bound live approval

Status: Proposed

## Decision
Evolve from a shared live confirmation token to short-lived single-use approval records bound to exact order intent, authenticated operator, expiry, and policy version.

## Consequences
Requires auth/RBAC and approval persistence; eliminates reusable frontend-style live authorization secrets.
