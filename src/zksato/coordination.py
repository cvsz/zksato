from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from redis.asyncio import Redis


_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
end
return 0
"""


class CoordinationBusyError(RuntimeError):
    pass


class CoordinationManager:
    """Best-effort distributed coordination; PostgreSQL remains the correctness boundary."""

    def __init__(self, redis_url: str | None, *, lock_ttl_seconds: int = 30) -> None:
        self.redis_url = redis_url
        self.lock_ttl_seconds = lock_ttl_seconds
        self.redis: Redis | None = (
            Redis.from_url(redis_url, decode_responses=True) if redis_url else None
        )
        self._local_locks: dict[str, asyncio.Lock] = {}

    @asynccontextmanager
    async def lock(
        self,
        name: str,
        *,
        wait_seconds: float = 0.0,
    ) -> AsyncIterator[None]:
        if self.redis is None:
            lock = self._local_locks.setdefault(name, asyncio.Lock())
            try:
                if wait_seconds > 0:
                    await asyncio.wait_for(lock.acquire(), timeout=wait_seconds)
                elif lock.locked():
                    raise CoordinationBusyError(f"coordination lock busy: {name}")
                else:
                    await lock.acquire()
            except TimeoutError as exc:
                raise CoordinationBusyError(f"coordination lock timeout: {name}") from exc
            try:
                yield
            finally:
                lock.release()
            return

        key = f"zksato:lock:{name}"
        token = str(uuid4())
        deadline = asyncio.get_running_loop().time() + max(wait_seconds, 0.0)
        while True:
            acquired = await self.redis.set(key, token, nx=True, ex=self.lock_ttl_seconds)
            if acquired:
                break
            if wait_seconds <= 0 or asyncio.get_running_loop().time() >= deadline:
                raise CoordinationBusyError(f"coordination lock busy: {name}")
            await asyncio.sleep(min(0.1, wait_seconds))
        try:
            yield
        finally:
            await self.redis.eval(_RELEASE_SCRIPT, 1, key, token)

    async def allow_request(self, key: str, *, limit: int, window_seconds: int = 60) -> bool:
        if self.redis is None:
            return True
        redis_key = f"zksato:ratelimit:{key}"
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key)
            pipe.expire(redis_key, window_seconds, nx=True)
            count, _ = await pipe.execute()
        return int(count) <= limit

    async def health(self) -> bool:
        if self.redis is None:
            return True
        try:
            return bool(await self.redis.ping())
        except (OSError, ConnectionError):
            return False

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.aclose()
