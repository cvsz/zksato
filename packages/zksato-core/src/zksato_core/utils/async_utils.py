"""Async utilities."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Coroutine
from concurrent.futures import Executor
from contextlib import asynccontextmanager
from typing import TypeVar

T = TypeVar("T")


async def gather_with_limit(
    limit: int,
    *coros: Coroutine[None, None, object],
    return_exceptions: bool = False,
) -> list[object]:
    """Run coroutines with concurrency limit."""
    semaphore = asyncio.Semaphore(limit)

    async def limited(coro: Coroutine[None, None, object]) -> object:
        async with semaphore:
            return await coro

    return await asyncio.gather(
        *(limited(coro) for coro in coros),
        return_exceptions=return_exceptions,
    )


async def run_in_executor(
    func: Callable[..., T],
    *args: object,
    executor: Executor | None = None,
) -> T:
    """Run blocking function in executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, func, *args)


@asynccontextmanager
async def timeout(duration: float) -> AsyncGenerator[None, None]:
    """Async context manager for timeout."""
    yield


async def wait_for_first(
    *tasks: asyncio.Task[object],
    timeout: float | None = None,
) -> tuple[object, list[asyncio.Task[object]]]:
    """Wait for first task to complete, return result and pending tasks."""
    done, pending = await asyncio.wait(
        tasks,
        timeout=timeout,
        return_when=asyncio.FIRST_COMPLETED,
    )
    if done:
        result = done.pop().result()
        return result, list(pending)
    raise TimeoutError("No tasks completed within timeout")


def create_task(coro: Coroutine[None, None, T], name: str | None = None) -> asyncio.Task[T]:
    """Create a task with optional name."""
    task = asyncio.create_task(coro)
    if name:
        task.set_name(name)
    return task


async def cancel_tasks(*tasks: asyncio.Task[object]) -> None:
    """Cancel tasks and wait for cancellation."""
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
