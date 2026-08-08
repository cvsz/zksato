# Engineering assurance model

zksato treats automated trading software as a safety-critical control plane. Source-code completion is not equivalent to broker, legal, deployment, or live-trading certification. This document defines the evidence gates that can be enforced by the repository and the gates that must remain external.

## Assurance layers

| Layer | Repository control | Evidence |
| --- | --- | --- |
| Source correctness | Ruff, full-repo format, mypy, compile, pytest | CI/Quality runs |
| Behavioral safety | deterministic risk tests, Hypothesis properties, OpenAPI safety contract | JUnit/coverage and test logs |
| Compatibility | Python 3.11-3.14 matrix | CI matrix |
| Durable state | PostgreSQL 16 migrations and integration tests | CI database service |
| Coordination | Redis integration and deterministic local fallback tests | CI/resilience |
| API contract | required safety-critical endpoints and forbidden live-TFEX paths | `openapi.json` artifact |
| Dependency security | runtime-only `pip-audit`, Bandit, Gitleaks | Security run |
| Workflow security | full-SHA action pins, least privilege, actionlint, zizmor | Governance/Workflow Lint |
| Container security | multi-stage non-root build, read-only runtime, dropped caps, Trivy, image SBOM | Container/Container Security |
| Supply chain | wheel/sdist validation, checksums, CycloneDX, GHCR digest, provenance | Release artifacts |
| Recovery | migration, backup, checksum, deliberate corruption, restore, sentinel | DR evidence JSON |
| Capacity | bounded local load test with explicit p95/failure thresholds | Performance evidence JSON |
| Release integrity | release checksum, clean wheel install, immutable GHCR digest and runtime test | Release Verification |
| Repository posture | read-only GitHub capability probes | Repository Health |
| UAT | protected, non-mutating deployed-UAT probe | UAT Certification |
| Production readiness | explicit runtime and external evidence, no execution | Production Readiness |

## Mandatory safety invariants

The repository must continue to enforce all of these invariants:

1. Paper mode is the default.
2. Autonomous live-money execution is forbidden.
3. Live equity execution remains downstream of deterministic server-side risk and explicit operator approval.
4. TFEX production mutation is unavailable until broker UAT certification is supplied externally.
5. Unknown broker outcomes move to reconciliation rather than blind retry.
6. Stale or unavailable trusted market data fails closed.
7. Broker credentials stay server-side.
8. Risk, order, approval, audit, and reconciliation behavior remains deterministic and testable.
9. A browser, AI model, agent, strategy, or workflow cannot grant itself live execution authority.
10. A passing repository build cannot self-certify broker permission, legal approval, production deployment, or a live canary.

## Pull-request gates

PRs should remain mergeable only after the source-controlled checks relevant to the change are green. The stable baseline is:

- `CI / Quality / Python 3.11`
- `CI / Compatibility / Python 3.11-3.14`
- `Quality / Format, types, contract, package and licenses`
- `Security / Python dependency and static security`
- `Workflow Lint / YAML, actionlint and zizmor` for workflow/config changes
- `PR Policy / Title and risk-sensitive change policy`
- `Container / Build and smoke test` for runtime/container changes
- `Container Security / Vulnerability, SBOM and hardened-runtime checks` for runtime/container changes
- `Resilience / Recovery and fail-closed` for risk/reconciliation/approval/persistence changes

`Dependency Review`, CodeQL, and artifact attestations remain capability-gated because private-repository availability depends on GitHub account/repository entitlements.

## Coverage and testing policy

The current branch-coverage floor is 65%. It is a ratchet, not a target. New production logic should be accompanied by tests that preserve or increase the measured value. Critical risk/execution paths should prefer direct deterministic assertions and property-based invariants over broad snapshot tests.

The normal suite excludes tests explicitly marked `uat` or `performance`. Those require a controlled execution context and have separate workflows.

## OpenAPI safety contract

`scripts/openapi_contract.py` exports the running FastAPI schema and `zksato.openapi_contract` validates high-value boundaries. The contract requires the risk preflight, live approval, order, reconciliation, production-readiness, and TFEX-UAT endpoints and explicitly rejects known live-TFEX mutation routes.

This is intentionally narrower than a generated whole-schema snapshot: it protects safety boundaries while allowing additive API evolution. Breaking API compatibility that affects clients should still be reviewed explicitly.

## Supply-chain policy

- External Actions are pinned to full 40-character commit SHAs.
- Release tags must match `pyproject.toml`.
- Python distributions must pass `twine check` and clean-install verification.
- Runtime dependencies are audited separately from build/test tooling.
- Runtime license inventory rejects AGPL/SSPL/GPLv3-class dependencies while not misclassifying LGPL dependencies.
- Release containers are scanned before publication.
- Release images are published by immutable digest to GHCR for amd64 and arm64.
- Dependency and image SBOMs plus SHA-256 checksums are release assets.
- GitHub artifact attestations remain optional/capability-gated for this private repository.

## Production-readiness evidence

The application and protected `Production Readiness` workflow require both runtime controls and external evidence. Runtime checks include production/live mode selection, live enablement, PostgreSQL, Redis, authentication, role credentials, session signing, trusted hosts, confirmation, distinct approval, explicit account allow-list, strict reference data, market-session enforcement, Settrade configuration, clear kill switch, broker reconciliation, and audit-chain integrity.

External evidence includes broker permission, legal/operational review, Settrade UAT completion, reconciled UAT orders, TLS, managed secrets, backup/restore, monitoring, incident response, rollback, capacity/SLO evidence, time synchronization, market-data failover behavior, data retention, release-artifact verification, and explicit manual-canary authorization.

Even after all gates pass, the generated canary plan remains non-autonomous and limited to one separately authorized manual order.

## GitHub settings that source code cannot complete

The following are external repository/account controls and must not be represented as complete until GitHub reports them as configured:

- protected `uat` and `production` environments and their required reviewers/secrets;
- branch protection/rulesets/merge queue where the current plan supports them;
- GitHub Secret Protection/secret scanning/push protection where available;
- GitHub Code Security/CodeQL and Dependency Review where available;
- artifact attestations where available for the private repository;
- repository Actions token policy and organization-level restrictions that the connected integration cannot mutate.

`Repository Health` records capability/API availability as evidence without converting a 403/plan limitation into a false source-code failure.
