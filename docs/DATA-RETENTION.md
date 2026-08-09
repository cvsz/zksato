# Data retention

## Categories
- Orders/fills/risk/audit/account snapshots: retain according to trading, audit, legal, and operational obligations.
- Market/research bars and strategy runs: retain according to research reproducibility/cost requirements.
- Logs/metrics/traces: retain long enough for incident diagnosis without retaining secrets.
- Backups: retain per DR policy and test restore before expiry.
- Sessions/transient coordination: shortest practical lifetime.

## Rules
Do not hard-code a universal production retention period in source without an approved policy. Production operators must define exact durations, deletion/archival procedures, legal holds, backup expiry, and access controls.

Deletion must preserve referential/audit requirements and must not silently destroy evidence needed to reconcile broker activity.
