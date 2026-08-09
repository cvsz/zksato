# Contributing to zksato

## Read first
Read `AGENTS.md`, `SECURITY.md`, `docs/INDEX.md`, `docs/DEVELOPMENT.md`, `docs/TESTING.md`, and any domain-specific ADR/runbook before changing code.

## Branch and commit conventions
Branch from `main` using a descriptive prefix such as `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `security/`, `risk/`, `strategy/`, `ci/`, or `ops/`.

Use Conventional Commit-style subjects: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `build:`, `ci:`, `chore:`, `security:`, `risk:`, or `strategy:`.

## Development flow
1. Define the problem, affected invariant, and acceptance criteria.
2. Inspect existing code/tests and relevant ADRs.
3. Implement one coherent vertical slice.
4. Add positive, negative, failure-path, and restart/idempotency coverage as relevant.
5. Update docs, schemas, migrations, runbooks, feature matrix, and ADRs affected by the change.
6. Run CI-equivalent validation.
7. Open a PR with rollout and rollback evidence.

## Required local validation
```bash
python -m pip install -e '.[dev,quality,security]'
python -m compileall -q src tests scripts
python -m pip check
ruff check .
ruff format --check .
mypy src/zksato scripts
pytest -m "not uat and not performance"
python scripts/openapi_contract.py
```

For infrastructure changes also run:
```bash
docker compose config
docker build -t zksato:local .
```

## Trading-sensitive changes
Changes to risk, execution, reconciliation, order identity, portfolio/P&L, Settrade integration, TFEX, auth/secrets, or trading-state migrations must document:
- deterministic failure behavior;
- idempotency/restart behavior;
- observability/audit impact;
- rollout and rollback;
- paper/UAT/live impact;
- proof that autonomous live-money execution is not introduced.

## Documentation and templates
Use `docs/templates/` for ADRs, RFCs, change requests, migrations, UAT evidence, DR drills, incidents, postmortems, security reviews, risk changes, strategy validation, and production readiness evidence.

## Pull requests
Keep PRs reviewable. Never mark an external gate complete without evidence. A red workflow caused by runner/account infrastructure is not equivalent to a source test failure, but the PR is also not CI-green until required checks actually run.
