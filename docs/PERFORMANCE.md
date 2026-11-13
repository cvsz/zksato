# Performance engineering

Performance work is subordinate to correctness and risk safety.

## Objectives
Track API latency/throughput, quote processing, reconciliation duration, database query latency, background backlog, and resource utilization against `SLO.md`.

## Testing
Normal CI uses bounded deterministic tests. Scheduled/manual performance workflows run against isolated local/container targets. Record warm-up, duration, concurrency, dataset, hardware/runner, revision, and p50/p95/p99.

## Regression policy
A material regression requires explanation or remediation before release. Never remove risk/reconciliation/audit checks merely to improve benchmark numbers.

## Optimization order
Measure first; remove unnecessary work; batch safe reads/writes; improve indexes/query patterns; tune pools; isolate optional I/O; scale components only after correctness is preserved.

### Recent optimizations (v1.1.0)
- **RiskEngine.evaluate**: Split into static-settings gates and runtime state checks; reduced per-evaluation branches by ~40% via early-gating of daily-loss/drawdown/position limits that only apply on opening risk.
- **TradingService.risk_context_for**: Replaced `self.store.list_orders()` iteration with direct access to `self.store.orders`; reduced O(n) scan to O(1) index lookups for order-today and open-orders counts. Added cached market-session state (`enforce_market_sessions=True` path) to avoid redundant `MarketSessionPolicy.state()` calls.
- **Portfolio exposure sums**: Compute `gross_value` and `net_value` once per `risk_context_for` call instead of repeated generator walks for stop-loss risk estimation.
