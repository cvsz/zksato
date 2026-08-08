# Performance and capacity

Correctness dominates latency optimization.

## Measure
Quote ingest throughput/lag, strategy evaluation latency, risk decision latency, broker round-trip latency, API p95/p99, reconciliation cycle duration/lag, DB query/lock latency, queue depth, dashboard update delay.

## Tests
Burst quotes, large watchlists, many open orders/fills, reconnect storms, DB contention, slow broker, backtest workloads.

## Guardrails
Backpressure/bounded queues, per-provider rate limits, no unbounded task creation, efficient indexes, pagination, and isolation of heavy backtests from execution-critical paths.
