# Production readiness and controlled rollout

`POST /v1/production/readiness` evaluates runtime controls together with operator-supplied external evidence. `POST /v1/production/canary-plan` can only produce a plan; it never submits an order.

Generate the machine-readable `ExternalReadinessEvidence` locally without submitting it:

```bash
python scripts/verify_external_gates.py --check-only
python scripts/verify_external_gates.py --base-url http://127.0.0.1:9569 --api-key "$READ_KEY" --manual-evidence evidence.json
curl -H "X-API-Key: $RISK_KEY" -H "Content-Type: application/json" \
  -d @readiness-input.json http://127.0.0.1:9569/v1/production/readiness | jq
```

A manual live canary requires durable PostgreSQL, authentication/RBAC, signed sessions, four-eyes approvals, account allow-list, strict reference data, market-session enforcement, successful reconciliation, valid audit chain, Settrade configuration, broker permission, legal/operational review, UAT evidence, TLS, managed secrets, backup/restore evidence, monitoring evidence, and explicit canary authorization.

The first live canary is one minimal-exposure operator-confirmed order. Reconcile expected versus broker order/fill/position state immediately afterwards. Risk limits may only increase through reviewed evidence and a version-controlled configuration change. Autonomous live-money execution remains out of scope.

For environment-specific unlock procedures, see [`docs/UNLOCK-RELEASE.md`](docs/UNLOCK-RELEASE.md).
