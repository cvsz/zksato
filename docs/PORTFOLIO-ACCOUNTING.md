# Portfolio and accounting

## Equity
Track cash, quantity, weighted average cost, market mark, market value, realized/unrealized P&L, fees/taxes where applicable, total equity and drawdown.

## TFEX
Use separate contract/margin/settlement semantics; do not reuse equity cost/cash logic blindly.

## Precision
Define decimal precision and rounding at broker/instrument boundaries. Persist broker-reported values alongside normalized calculations where useful.

## Reconciliation
Compare local positions/cash/orders/fills to broker snapshots on startup and periodically. Differences create auditable reconciliation events; never silently overwrite unexplained drift.
