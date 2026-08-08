# Skill: security hardening

## Workflow
Update threat model → identify assets/actors/trust boundaries → add authn/authz → secret management/rotation → input/rate/CSRF/CORS protections → redaction/audit → dependency/container scanning → tests.

## High-risk assets
Broker credentials/PINs, live confirmation authority, sessions, order mutation endpoints, audit trail, strategy/risk configuration.
