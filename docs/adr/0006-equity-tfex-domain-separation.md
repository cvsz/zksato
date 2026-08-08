# ADR-0006: Separate equity and TFEX domain semantics

Status: Accepted target

## Decision
Share generic interfaces only where semantics truly match; model TFEX contracts, long/short, open/close, margin, settlement, expiry/rollover separately from equity.

## Consequences
More domain code, fewer dangerous hidden assumptions.
