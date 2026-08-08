# Dashboard requirements

## Operator hierarchy
Mode/environment and health → feed freshness → cash/equity/P&L → risk/kill switch → positions → open orders/fills → signals → automation controls → audit/alerts.

## Safety UX
Paper/sandbox/live must be visually unmistakable. Synthetic data must be labeled. Money-moving actions show account, symbol, side, quantity, price/order type, estimated notional/risk, and require authenticated confirmation where policy requires.

## Target enhancements
Realtime websocket/SSE updates, auth/RBAC, strategy parameter editor with version history, risk admin panel, reconciliation status, broker connectivity, incident banner, exportable audit/reporting, mobile-safe monitoring.

Frontend never owns the authoritative risk/live-execution decision.
