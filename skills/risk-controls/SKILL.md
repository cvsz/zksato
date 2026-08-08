# Skill: risk controls

## Workflow
- Define measurable invariant and required inputs.
- Decide fail-open vs fail-closed; trading safety defaults to fail-closed.
- Implement deterministic rule in risk layer.
- Cover boundary, missing-input, stale-data, and kill-switch cases.
- Surface reason codes/audit evidence.
- Update risk docs and feature matrix.

## Never
Do not allow frontend/strategy/AI to override server policy.
