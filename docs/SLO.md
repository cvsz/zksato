# Service-level objectives

Production SLOs are operational gates, not promises made by source code alone.

| Signal | Objective | Failure action |
|---|---:|---|
| trusted quote freshness | <= `ZKSATO_SLO_FEED_FRESHNESS_SECONDS` | block new exposure; investigate feed |
| unresolved reconciliation | <= `ZKSATO_SLO_RECONCILIATION_BACKLOG_MAX` | block broker execution |
| API p95 latency | <= `ZKSATO_SLO_API_P95_MS` | investigate saturation/dependencies |
| PostgreSQL health | 100% while execution enabled | disable execution |
| Redis coordination health | healthy for multi-replica deployment | fail to single active operator or disable mutations |
| audit-chain verification | valid | freeze privileged mutation and export evidence |

Prometheus rules are in `deploy/monitoring/alerts.yml`. Alert thresholds must be reviewed against production traffic before rollout.
