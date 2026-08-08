# GitHub Actions operations

This document complements `docs/GITHUB.md` with the final automation controls added after the production-grade Actions baseline.

## Production Readiness workflow

`.github/workflows/production-readiness.yml` is manual-only and uses the protected GitHub environment `production`. It does not submit, cancel, or modify broker orders.

The workflow requires an HTTPS zksato endpoint, the literal confirmation `READINESS_ONLY`, externally supplied readiness evidence, and an environment-scoped API credential permitted to call the zksato readiness evaluation boundary. Configure required reviewers on the `production` environment and keep the credential outside repository variables, workflow inputs, and committed files.

It calls only:

- `POST /v1/production/readiness`
- `POST /v1/production/canary-plan`

The workflow uploads the evidence payload, readiness report, and non-executing canary plan as a 30-day Actions artifact, then fails closed unless the application reports `ready_for_manual_canary=true`, the plan reports `allowed=true`, and `autonomous_execution=false`.

Passing this workflow is evidence for a separately authorized manual canary. It is not approval for autonomous trading.

## Release container artifacts

The tag-driven `Release` workflow publishes both Python release files and a versioned container artifact to GitHub Container Registry:

- `ghcr.io/cvsz/zksato:<tag>`
- `ghcr.io/cvsz/zksato:latest`

BuildKit provenance and container SBOM metadata are enabled. The immutable digest is written to `CONTAINER_IMAGE.txt` and included with the Python dependency SBOM and SHA-256 release checksums.

The release workflow publishes artifacts only; it does not deploy production infrastructure or connect the image to a brokerage account.

## Dependency maintenance

Dependabot monitors Python packages, GitHub Actions, and Docker references on a weekly `Asia/Bangkok` schedule. All resulting pull requests must pass repository CI, governance, security, and any path-relevant container checks.

## External GitHub settings

Repository source cannot create or certify these settings. Configure them in GitHub repository settings:

1. Protect `main` with required CI/Governance/Security checks and reviewed pull requests.
2. Protect the `uat` and `production` environments with required reviewers.
3. Enable secret scanning/push protection and Dependabot security alerts where available.
4. Enable CodeQL, Dependency Review, and artifact attestations only when the repository/account plan supports the corresponding capability gates documented in `docs/GITHUB.md`.
5. Define GHCR visibility and retention policy appropriate for this private repository.
