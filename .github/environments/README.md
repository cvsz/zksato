# GitHub environment contract

`requirements.json` is the machine-readable desired-state contract for GitHub Environments used by zksato.

It defines only configuration that is safe to keep in Git:

- environment names;
- workflow ownership;
- whether the job should create deployment history;
- branch/tag deployment restrictions;
- required secret **names**;
- required non-secret variable names;
- safe default capability flags;
- the explicit runtime-secret boundary.

Secret values are never stored here.

Use `scripts/github_environment_admin.py audit` to compare GitHub with the contract and `apply` from a trusted administrator workstation to create/update non-secret environment configuration. See `docs/GITHUB-ENVIRONMENTS.md` for token permissions, secure secret installation and rotation.

The contract must never add broker/runtime credentials to GitHub Actions merely for convenience. Settrade App Secret/PIN, database/Redis credentials, session/API secrets and notification webhooks remain deployment/runtime secret-manager concerns.
