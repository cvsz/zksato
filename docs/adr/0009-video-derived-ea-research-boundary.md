# ADR 0009 — Video-derived EA stays outside trusted execution

## Status
Accepted.

## Context
Three supplied trading videos expose useful behavioral hypotheses: price-action zone confirmation, breakout/retest structure, a fixed-step stop ladder, basket flatten/reset, and extreme duplicate position stacking. The recordings do not reveal complete hidden EA logic and do not provide statistical evidence of profitability or safe tail behavior.

SET equity execution also differs materially from the XAUUSD MetaTrader examples, especially around short exposure, tick rules, sessions, price bands, broker order semantics and account controls.

## Decision
Implement the reconstructed strategy as a **non-executing research planner and virtual cycle runtime**.

- `src/zksato/video_ea.py` converts OHLC candles into PA bias, zone, bounded virtual ladder and invalidation metadata.
- `src/zksato/video_ea_runtime.py` arms plans, detects/deduplicates virtual crossings and evaluates basket/invalidation state without broker calls.
- SET-equity mode rejects symmetric long/short grids and does not create naked short ladders.
- Fixed sizing and hard quantity/trigger caps replace the unbounded stacking visible in the recordings.
- Martingale sizing is intentionally absent.
- Any actual SET order must be reconstructed from trusted server-side data and pass `TradingService` and `RiskEngine` plus existing operator/live-approval controls.
- The MQL5 file under `ea/` is an isolated Strategy Tester/demo reference and refuses real-account initialization.

## Consequences
The video hypothesis can be replayed, tested and refined without increasing live execution authority. There is no direct one-click path from video-derived trigger to broker mutation. Production promotion requires normal research evidence, Settrade Sandbox/UAT verification and existing operational approvals.

This design intentionally trades convenience for auditability, deterministic risk control and failure isolation.
