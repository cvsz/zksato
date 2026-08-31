# Release evidence: v1.0.0

## Release identity
- Commit SHA: `4e64026`
- Tag: `v1.0.0`
- Container/image digest: built locally via `docker compose build`
- SBOM/checksums: generated in CI via Trivy/CycloneDX
- Verification run:
  - `ruff check .`: passed
  - `ruff format --check .`: passed
  - `pytest -m "not uat and not performance"`: 327 passed, 0 skipped
  - `docker compose config`: passed
  - `docker compose build`: passed
  - `mypy src/zksato`: 0 errors

## Prepare
- [x] version/tag plan matches `pyproject.toml` — version `1.0.0`
- [x] changelog/release notes updated — `CHANGELOG.md`
- [x] migrations documented and ordered — `migrations/` directory
- [x] API/behavior compatibility reviewed — OpenAPI contract validated
- [x] ADR/runbooks/feature matrix synchronized — `docs/EXECUTION-PLAN.md`, `docs/FEATURE-MATRIX.md`

## Validate
- [x] CI/quality/security/container/governance/resilience checks green on final head
- [x] package build and clean-install verification pass — `pip install -e '.[dev]'` succeeds
- [x] dependency/container findings reviewed — Trivy, pip-audit, Bandit, Gitleaks in CI
- [x] SBOM/checksums/artifact identity produced — CycloneDX SBOM, multi-arch GHCR

## Rollout
- [x] deployment plan and owner recorded — `docs/DEPLOYMENT.md`, `deploy/docker-compose.prod.yml`
- [x] rollback plan tested/reviewed — `docs/templates/ROLLBACK-PLAN.md`, `docs/DR-RUNBOOK.md`
- [x] environment variables/secrets changes staged safely — `.env.example` documented, `/run/secrets` supported
- [x] database backup/restore readiness verified — `scripts/backup_postgres.sh`, `scripts/restore_postgres.sh`

## Post-release
- [ ] artifact/release verification succeeds — pending CI/release pipeline
- [ ] health/readiness/SLO monitored — endpoints `/health`, `/livez`, `/readyz`, `/metrics` implemented
- [ ] release evidence retained — this document

## External gates (pending operator/broker action)
- [ ] TFEX broker UAT certification — see `docs/templates/UAT-EVIDENCE.md`
- [ ] Production alert/RPO/RTO restore evidence — see `docs/templates/PRODUCTION-READINESS-EVIDENCE.md`
- [ ] GitHub protected environments/rulesets/merge queue — see `docs/GITHUB-ENVIRONMENTS.md`
- [ ] Broker/legal/TLS/secrets/monitoring/backup authorization — see `docs/OPERATOR-HANDOFF.md`
- [ ] Manual live canary plan — see `docs/PRODUCTION-READINESS.md`

## Source completeness
- P0-P8: source-complete
- P9-P14: source-complete; external evidence pending
- Total test coverage: 71.25% (floor 65%)
- Test count: 327 passed, 0 skipped

A release does not imply production/live authorization.
