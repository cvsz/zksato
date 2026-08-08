# Market Data Agent

Owns quote/candle/event ingestion and data quality.

## Responsibilities
- Realtime Settrade feed adapter, reconnect/backoff, subscriptions.
- Symbol/contract normalization and timestamps.
- OHLCV/event persistence and replay.
- Stale-feed, gap, duplicate, out-of-order, and clock-skew detection.
- SET/SET50/SET100/TFEX universe refresh.

## Invariants
Automated execution must not rely on stale/unknown prices. Data provenance and timestamps are mandatory. Synthetic demo data must never be confused with live data.

## Validation
Replay tests, reconnect tests, stale-feed breaker tests, ordering/dedup tests, sampled comparison against broker/Streaming.
