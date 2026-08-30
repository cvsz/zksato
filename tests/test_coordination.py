from __future__ import annotations

import asyncio

import pytest

from zksato.coordination import CoordinationBusyError, CoordinationManager


@pytest.mark.asyncio
async def test_coordination_local_lock_basic_acquire_and_release() -> None:
    mgr = CoordinationManager(redis_url=None)
    async with mgr.lock("my-resource"):
        pass  # must not raise


@pytest.mark.asyncio
async def test_coordination_local_lock_busy_raises() -> None:
    mgr = CoordinationManager(redis_url=None)
    lock = asyncio.Lock()
    await lock.acquire()
    # Inject a pre-acquired asyncio.Lock into the manager's internal registry
    mgr._local_locks["busy-resource"] = lock
    with pytest.raises(CoordinationBusyError, match="coordination lock busy"):
        async with mgr.lock("busy-resource", wait_seconds=0.0):
            pass
    lock.release()


@pytest.mark.asyncio
async def test_coordination_local_lock_wait_timeout_raises() -> None:
    mgr = CoordinationManager(redis_url=None)
    lock = asyncio.Lock()
    await lock.acquire()
    mgr._local_locks["slow-resource"] = lock
    with pytest.raises(CoordinationBusyError, match="coordination lock"):
        async with mgr.lock("slow-resource", wait_seconds=0.05):
            pass
    lock.release()


@pytest.mark.asyncio
async def test_coordination_local_rate_limit_always_allows_when_no_redis() -> None:
    mgr = CoordinationManager(redis_url=None)
    for _ in range(200):
        assert await mgr.allow_request("some-key", limit=10, window_seconds=60) is True


@pytest.mark.asyncio
async def test_coordination_health_returns_true_without_redis() -> None:
    mgr = CoordinationManager(redis_url=None)
    assert await mgr.health() is True


@pytest.mark.asyncio
async def test_coordination_close_noop_without_redis() -> None:
    mgr = CoordinationManager(redis_url=None)
    await mgr.close()  # must not raise
