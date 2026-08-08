# Development guide

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
ruff check .
pytest
uvicorn zksato.api:app --reload --port 9569
```

## Principles
Typed domain models, deterministic core logic, async for I/O boundaries, dependency inversion around broker/storage/feed providers, explicit errors, no secret logging, small vertical slices.

## Adding a feature
Read `AGENTS.md`; choose specialist agent/skills; define acceptance/failure behavior; implement tests with code; update docs/feature matrix/ADR where applicable; run CI-equivalent checks; open PR with rollout/rollback.

## Local safety
Keep paper mode default. Do not place real Settrade secrets in `.env` files that may be shared or committed.
