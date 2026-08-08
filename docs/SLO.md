# Service levels and operational objectives

Initial targets must be measured and refined before production commitments.

## Suggested internal objectives
- Health/control API availability: 99.9% during intended service window.
- Market feed freshness: within configured instrument/feed threshold while automation enabled.
- Reconciliation: no unresolved live unknown order beyond a defined short operational threshold without alert.
- Audit completeness: 100% of money-moving attempts correlated to risk/authorization/order outcome.
- RPO for durable order/audit DB: near-zero with transactional storage; backups provide disaster recovery layer.

SLO breaches should trigger documented incident/runbook actions, not automatic risk-limit relaxation.
