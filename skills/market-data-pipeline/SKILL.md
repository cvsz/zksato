# Skill: market data pipeline

## Workflow
Define source → normalize symbol/contract/timestamp → validate ordering/dedup → persist/replay → expose snapshot/stream → monitor freshness.

## Required controls
Reconnect with bounded backoff, stale-feed detection, gap handling, clock-skew visibility, provenance, synthetic/live separation.

## Tests
Duplicate/out-of-order events, disconnect/reconnect, stale threshold, replay determinism, malformed payloads.
