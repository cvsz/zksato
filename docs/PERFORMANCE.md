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
