"""Functional programming utilities."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")


def pipe(*funcs: Callable[..., object]) -> Callable[[object], object]:
    """Compose functions left-to-right: pipe(f, g, h)(x) = h(g(f(x)))."""

    def composed(x: object) -> object:
        result = x
        for f in funcs:
            result = f(result)
        return result

    return composed


def compose(*funcs: Callable[..., object]) -> Callable[[object], object]:
    """Compose functions right-to-left: compose(f, g, h)(x) = f(g(h(x)))."""
    return pipe(*reversed(funcs))


def identity(x: T) -> T:
    """Identity function."""
    return x


def constant(value: T) -> Callable[..., T]:
    """Return a function that always returns the given value."""

    def const_func(*args: object, **kwargs: object) -> T:
        return value

    return const_func


def tap(func: Callable[[T], object]) -> Callable[[T], T]:
    """Apply function for side effects, return original value."""

    def wrapper(x: T) -> T:
        func(x)
        return x

    return wrapper


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry decorator with exponential backoff."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_delay = delay
            last_exception: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
            assert last_exception is not None
            raise last_exception

        return wrapper

    return decorator


async def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, Coroutine[Any, Any, R]]], Callable[P, R]]:
    """Retry decorator for async functions with exponential backoff."""

    def decorator(func: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, R]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_delay = delay
            last_exception: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            assert last_exception is not None
            raise last_exception

        return cast(Callable[P, R], wrapper)

    return decorator
