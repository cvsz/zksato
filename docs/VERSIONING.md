# Versioning

zksato uses semantic-versioning intent for release tags and package versions.

- MAJOR: incompatible public API/data/operational contract changes.
- MINOR: backward-compatible features or material capability additions.
- PATCH: backward-compatible fixes/security/reliability improvements.

Release tags use `vX.Y.Z` and must match `pyproject.toml`. Migrations are monotonic ordered SQL files and are not renumbered after release. Strategy versions are independent immutable domain identifiers and must not be conflated with package versions.

Pre-release/testing builds may use explicit prerelease identifiers when the release workflow supports them. A Git tag is a release artifact trigger, not production authorization.
