# Secrets management

## Secrets
Settrade app secret/PIN/session credentials, authentication signing keys, database credentials, notification credentials, live approval material.

## Target
Managed secret store or orchestrator-native secret injection with least privilege, rotation, versioning, and audited access.

## Prohibited
Git commits, Docker image layers, frontend bundles, query strings, screenshots, test fixtures, logs/traces/metrics labels, public issue/PR text.

## Rotation
Document owner, rotation interval/event, dual-key transition if needed, rollback, service reload/restart behavior, and validation that old material is revoked.
