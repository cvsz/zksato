# Coding standards

## Python
- Python 3.11+; typed interfaces for public/service boundaries.
- Prefer small deterministic functions for risk/accounting/order-state logic.
- Use Pydantic models for validated domain/API payloads.
- Avoid hidden mutable globals in correctness-sensitive paths.
- Time values must be timezone-aware at domain boundaries.
- No provider/broker secrets in client code, logs, exceptions, tests, fixtures, or snapshots.

## Quality gates
`ruff check .`, `ruff format --check .`, mypy, compile checks, pytest/branch coverage, OpenAPI contract checks, package validation, dependency/security checks, and relevant Docker/SQL validation.

## Error handling
Fail closed for execution prerequisites. Preserve causal errors without leaking secrets. Distinguish retryable transport errors, validation errors, ambiguous broker outcomes, and permanent policy rejection.

## State changes
Money-moving/stateful operations require idempotency, explicit status transitions, durable evidence, and restart behavior. Migrations must be ordered and documented.

## Tests
Test behavior, not implementation trivia. Include negative/failure/restart/concurrency cases for high-risk code. Never require real-money credentials in normal CI.
