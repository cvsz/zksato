# Risk administrator guide

Risk administrators manage policy and evidence; they do not bypass it.

## Review
Inspect account allow-list, market/session/reference requirements, position/order/notional limits, gross/net/symbol/sector exposure, daily loss/drawdown, stop-loss policy, short-selling policy, TFEX-specific limits, and kill switch.

## Before live manual approval
Confirm server-derived context, fresh broker reconciliation, no unresolved order state, correct account, verified calendar/reference data, configured auth, and intent-bound approval requirements.

## Changes
Use the Risk Change issue/PR/template. Include boundary/property tests, expected reject reasons, rollout/rollback, and audit/observability impact.

Never relax a limit merely because a strategy or agent requests execution.
