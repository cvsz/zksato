# Observability

## Target stack
Prometheus-compatible metrics, OpenTelemetry traces, structured logs, Grafana dashboards, Loki or equivalent log backend.

## Correlation
Use request/correlation IDs and stable IDs for strategy run, signal, risk decision, order intent, local order, broker order, fill, and reconciliation cycle.

## Core metrics
Feed age/reconnects; broker request latency/errors; order states/fills/rejects; unknown orders; reconciliation lag/drift; risk rejections by reason; exposure/P&L/drawdown; bot state; DB pool/latency; Redis/queue health; auth failures; kill switch.

## Alerts
SEV-1: uncontrolled/unknown live order state, reconciliation drift with monetary impact, credential compromise suspicion. SEV-2: stale feed while automation enabled, sustained broker failure, DB unavailable. Every alert links to a runbook.

## Redaction
Never emit PINs, app secrets, tokens, cookies, authorization headers, or full confidential request payloads.
