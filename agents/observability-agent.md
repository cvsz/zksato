# Observability Agent

Owns metrics, structured logs, traces, dashboards, and alerts.

## Critical telemetry
Broker latency/errors, feed freshness, order lifecycle counts, reconciliation lag, risk rejects, exposure, P&L/drawdown, bot state, DB/Redis health, queue lag, auth failures, kill-switch state.

## Rules
Never log secrets. Correlate signal → risk decision → order intent → broker order → fill using stable IDs. Define actionable SLOs and alert runbooks.
