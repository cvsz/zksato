---
applyTo: "src/zksato/{risk,service,reconcile,session_reconcile,portfolio,tfex}.py"
---
Money-moving behavior must be deterministic, idempotent, auditable, restart-safe, and fail closed on stale/unknown prerequisites. Preserve local economic order identity during broker reconciliation. Broker state is external truth for reconciliation; never guess an ambiguous outcome or automatically retry a possibly accepted live order.
