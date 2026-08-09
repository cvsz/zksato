# Troubleshooting

## Service will not become ready
Check `/health` and `/readyz`. Typical causes: database health, Redis/coordination health, invalid audit chain, or non-paper reconciliation not yet ready. A restart intentionally clears broker reconciliation readiness until a fresh snapshot succeeds.

## Orders are rejected
Inspect the returned risk reasons and `/v1/risk/evaluations`. Check market-data freshness, market session, account allow-list, tick/price band, notional/exposure, daily loss/drawdown, available quantity/line, open-order limits, stop-loss requirement, kill switch, and approval/reconciliation state.

## Settrade integration fails
Verify server-side credentials/configuration and broker account permissions. Reproduce in the broker UAT environment. Do not infer API signatures or production permission from paper tests.

## Dashboard/API unavailable
Confirm port `9569`, container/process health, reverse-proxy routing, trusted hosts, CORS, auth, and firewall policy.

## Database migration fails
Stop rollout, preserve the error and database state, follow `migrations/README.md` and the migration template, then restore/rollback according to the documented plan. Never skip a failed trading-state migration and continue deployment.

## GitHub Actions fail before any steps
Inspect check annotations. Billing/spending/runner availability, plan-gated security features, or environment configuration can prevent a job from starting; this is infrastructure evidence, not a passing source validation.

## Incident involving live exposure
Stop automation, engage kill switch, verify/cancel broker orders through the approved interface, preserve evidence, and follow `docs/INCIDENT-RESPONSE.md`.
