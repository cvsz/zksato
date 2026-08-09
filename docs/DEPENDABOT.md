# Dependabot policy

`.github/dependabot.yml` is authoritative for configured ecosystems and cadence.

Current intended surfaces include Python/pip, GitHub Actions, and Docker. Group related safe updates, cap concurrent PRs, and use rebase/update behavior to keep changes reviewable.

Dependabot PRs are not exempt from CI/security/license/container checks. Broker SDK and major-version upgrades require explicit compatibility review and UAT where behavior is broker-sensitive.

Do not auto-merge an update solely because Dependabot created it; automation may be added only for narrowly classified updates with required checks and rollback confidence.
