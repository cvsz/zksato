# Capacity planning

## Inputs
Measure request rate, quote/bar ingest rate, symbols/subscriptions, order/reconciliation volume, database growth, audit/outbox growth, worker concurrency, latency percentiles, CPU/memory, connection pools, Redis operations, and retention period.

## Method
1. Define expected and peak workload.
2. Run bounded performance tests in an isolated non-production environment.
3. Measure p50/p95/p99, throughput, errors, queue/backlog, DB/Redis saturation, and resource headroom.
4. Set scaling limits and alerts.
5. Re-run after material architecture/dependency changes.

## Safety
Load tests must not target production broker mutation endpoints. Capacity evidence cannot authorize live trading.

## Output
Use `docs/templates/PERFORMANCE-REPORT.md` and attach measured environment/configuration, results, bottlenecks, and approved headroom.
