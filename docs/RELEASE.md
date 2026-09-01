# Release process

## Release candidate gates
Green CI; no unresolved critical security/risk issue; changelog updated; feature matrix truthful; migrations tested; runbooks/rollback ready; UAT evidence for broker changes; observability/alerts ready.

## Versioning
Use semantic versioning where possible. Record Git commit and version in runtime diagnostics.

## Promotion
Development → paper validation → UAT for broker-affecting changes → staged production. Live-sensitive rollout begins with explicit operator approval and minimal exposure.

For environment-specific unlock procedures during promotion, see `UNLOCK-RELEASE.md`.

## Release notes
Summarize features, fixes, security/risk changes, API/schema changes, migrations, operational steps, known limitations, rollback procedure.
