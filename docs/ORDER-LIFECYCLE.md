# Order lifecycle

## Target state machine
`intent_created` → `submit_pending` → (`accepted/open` | `rejected` | `unknown`) → optional `partially_filled` → (`filled` | `cancel_pending` → `cancelled` | `unknown`). Reconciliation may transition unknown/open states based on broker evidence.

## Idempotency
Client idempotency key is durable and unique per account/business action. Repeated identical requests return/reconcile the existing action rather than creating a second broker order.

## Ambiguity
A transport error after broker request transmission is not safe to retry until broker state is queried. Record `unknown` and reconcile.

## Correlation
Signal, risk decision, approval, local order, broker order, fills, and audit events share correlation/causation identifiers.
