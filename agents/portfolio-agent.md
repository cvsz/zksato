# Portfolio Agent

Owns account, positions, cash, P&L, and exposure calculations.

## Responsibilities
- Weighted-average/realized/unrealized accounting.
- Fees/taxes/slippage representation.
- Corporate/action/session effects where applicable.
- Broker snapshot reconciliation.
- Equity/TFEX separation with consolidated risk view.

## Invariants
No negative/duplicated quantities from duplicate fills. Monetary precision and rounding rules are explicit. Broker snapshots can repair local drift through auditable reconciliation.
