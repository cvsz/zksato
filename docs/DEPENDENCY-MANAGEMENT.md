# Dependency management

## Policy
Dependencies must have a clear runtime/dev purpose, compatible license, maintained source, bounded version range/pin appropriate to risk, and no known unacceptable vulnerability at release time.

## Automation
Dependabot covers Python, GitHub Actions, and Docker update surfaces. Automated PRs still require normal validation. External Actions must remain pinned to immutable commit SHAs.

## Review
For material dependency changes review API/behavior compatibility, transitive graph, security advisories, license, Python/platform support, container impact, and rollback.

## Broker SDK
Settrade SDK changes are integration-sensitive. Pin reviewed versions and validate signatures/behavior in broker UAT before claiming compatibility.

## Removal
Remove unused dependencies promptly and regenerate relevant SBOM/license evidence.
