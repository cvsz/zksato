# Release checklist

## Prepare
- [ ] version/tag plan matches `pyproject.toml`
- [ ] changelog/release notes updated
- [ ] migrations documented and ordered
- [ ] API/behavior compatibility reviewed
- [ ] ADR/runbooks/feature matrix synchronized

## Validate
- [ ] CI/quality/security/container/governance/resilience checks green on final head
- [ ] package build and clean-install verification pass
- [ ] dependency/container findings reviewed
- [ ] SBOM/checksums/artifact identity produced

## Rollout
- [ ] deployment plan and owner recorded
- [ ] rollback plan tested/reviewed
- [ ] environment variables/secrets changes staged safely
- [ ] database backup/restore readiness verified if migration-sensitive

## Post-release
- [ ] artifact/release verification succeeds
- [ ] health/readiness/SLO monitored
- [ ] release evidence retained

A release does not imply production/live authorization.
