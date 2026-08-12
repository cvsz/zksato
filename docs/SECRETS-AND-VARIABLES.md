# GitHub secrets and variables

## Secrets
Use environment/repository secrets only for data that must remain confidential. Prefer environment-scoped secrets for UAT/production. Never store secrets in repository variables, issue bodies, artifacts, cache keys, logs, or example files.

## Variables
Use repository/environment variables for non-secret capability toggles such as optional plan-dependent workflow features. Defaults should fail safely when a capability is unavailable.

## Rotation
Document owner, purpose, scope, rotation/revocation method, dependent workflows, and emergency rotation procedure outside the secret value itself.

## Known categories
UAT API credentials, production risk/readiness API credentials, optional cloud/OIDC configuration, and capability flags. Exact names are documented by the workflows that consume them.
