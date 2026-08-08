# Changelog

All notable changes to zksato are documented here.

## Unreleased

### Repository assurance and delivery
- Added a full engineering-assurance layer: Ruff full-repository formatting, mypy, branch coverage, Hypothesis risk invariants, safety-critical OpenAPI contract validation, package metadata checks, and runtime dependency license policy.
- Added independent workflow hardening with immutable external Action SHAs, YAML/actionlint/zizmor validation, ShellCheck, Hadolint, PR title/risk-evidence policy, and safe path-based labeling without `pull_request_target`.
- Added runtime-only dependency auditing, Bandit, Gitleaks, high-confidence secret patterns, and capability-gated CodeQL/Dependency Review.
- Added Trivy container vulnerability evidence, fixed-critical blocking, image CycloneDX SBOM generation, multi-stage minimal Docker runtime, and hardened read-only/no-capabilities/no-new-privileges smoke tests.
- Added multi-architecture GHCR release publication, dependency/image SBOMs, immutable image digest recording, provenance, checksums, optional attestations, and independent release verification.
- Added read-only repository-capability health evidence for environments, protection/rulesets, Actions, code/secret scanning, and Dependabot APIs.
- Added bounded performance SLO evidence, measured PostgreSQL backup/restore evidence with corruption detection, and deterministic resilience tests across multiple hash seeds.
- Added developer parity files: `Makefile`, pre-commit configuration, EditorConfig, Docker ignore, YAML/Hadolint/Gitleaks policies.

### Runtime and safety hardening
- Strengthened production-readiness gates to require explicit production/live selection, durable PostgreSQL/Redis, authentication credentials/session signing/trusted hosts, four-eyes confirmation, explicit account allow-list, strict reference/session controls, Settrade configuration, clear kill switch, reconciliation, audit-chain integrity, and broader external operational evidence.
- Production readiness remains non-executing and the canary plan remains non-autonomous with a maximum of one separately authorized order.
- Fixed FastAPI dynamic cookie dependency annotations so OpenAPI generation is stable and testable.
- Fixed package runtime version reporting to use installed distribution metadata and added a version single-source-of-truth test.
- Tightened paper-state restoration, strategy optional-value handling, approval repository typing, Redis coordination typing, and UAT response validation discovered by the full mypy gate.

## 0.4.0
- P0-P6 source-complete risk-first platform baseline with durable state, reconciliation, market/risk controls, RBAC/approvals, TFEX UAT isolation, observability/DR primitives, research promotion gates, and non-executing production-readiness controls.
- Production port standardized on `9569`.
- Autonomous live-money execution remains forbidden by design.
