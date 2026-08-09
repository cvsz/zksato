# Environments

## Local development
Default `paper`, local/memory or Docker PostgreSQL/Redis, no production credentials. Port `9569`.

## Test/CI
Ephemeral services and synthetic credentials/data only. Normal CI excludes broker UAT and destructive production actions.

## Broker UAT/sandbox
Uses broker-issued non-production credentials and explicit certification evidence. UAT proves only the tested account/environment/revision and does not imply production permission.

## Production
Requires authenticated TLS deployment, PostgreSQL correctness store, Redis coordination where configured, managed secrets, verified reference/calendar data, monitoring/alerts, backups/restore evidence, incident/rollback readiness, broker/legal/operational permission, reconciliation readiness, and explicit manual canary authorization.

## GitHub environments
Target `uat` and `production` environments with protected secrets/reviewers where supported. Their actual existence/settings are external GitHub state and must be verified rather than inferred from workflow YAML.
