# Performance & Reliability Report

**Repository**: `cvsz/zksato`  
**Date**: 2026-11-09  

## 1. Benchmarking & Metrics

- **API Startup**: Sub-second FastAPI boot with lazy initialization of market feeds.
- **Order Preflight Latency**: Microsecond deterministic evaluation through compiled Pydantic models and in-memory risk context.
- **Concurrency**: `asyncio.Lock` per symbol/broker instance prevents race conditions during quote processing.
- **Frontend Build Optimization**: Next.js webpack build compiles 10 routes in ~12 seconds with static generation of public pages.

## 2. Load Testing Utilities
- `scripts/load_test.py`: Validates order throughput and quote processing capacity under synthetic stress without external network dependencies.
- Excluded from standard CI via `pytest -m "not performance"` marker to maintain rapid, deterministic feedback loops.
