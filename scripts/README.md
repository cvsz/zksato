# Operational scripts

Used by CI, the `Makefile`, and operators. Shell scripts must pass `shellcheck`.

| Script | Purpose |
|--------|---------|
| `openapi_contract.py` | Generate/validate `openapi.json` (`make openapi`) |
| `load_test.py` | Bounded HTTP load probe for SLO verification |
| `uat_certify.py` | Settrade UAT certification evidence |
| `verify_external_gates.py` | External gate readiness + operator checklist |
| `github_environment_admin.py` | Export/apply GitHub environment settings (`github-environments.json`) |
| `github_health.py` | Repository health checks |
| `video_ea_plan.py`, `video_evidence_extract.py` | Video EA research tooling |
| `backup_postgres.sh`, `restore_postgres.sh` | PostgreSQL backup / restore |
| `provision_zksato_infra.sh` | Host infrastructure provisioning |
| `cloudflare-tunnel-add-zksato.sh` | Add zksato route to the Cloudflare tunnel |
