# Contributing to zksato

## Development flow
1. Create an issue or reference an existing roadmap item for non-trivial work.
2. Branch from `main` using `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, or `ops/`.
3. Implement one coherent vertical slice.
4. Add tests and update affected documentation.
5. Run `ruff check .` and `pytest`.
6. Open a PR using the repository template.

## Commit style
Use conventional prefixes: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `build:`, `ci:`, `chore:`, `security:`.

## Trading-sensitive changes
Changes to risk, execution, reconciliation, portfolio accounting, Settrade integration, TFEX, or secrets must include explicit failure behavior, rollback steps, and tests proving fail-closed behavior.

## Pull requests
Keep PRs reviewable. Describe scope, risk, tests, migrations, monitoring, rollout, rollback, and whether paper/UAT/live behavior changes.

See `AGENTS.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`, and `docs/GITHUB.md`.
