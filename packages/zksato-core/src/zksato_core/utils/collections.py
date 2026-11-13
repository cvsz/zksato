"""Collection utilities."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


def group_by(items: list[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    """Group items by key function."""
    result: dict[K, list[T]] = defaultdict(list)
    for item in items:
        result[key(item)].append(item)
    return dict(result)


def index_by(items: list[T], key: Callable[[T], K]) -> dict[K, T]:
    """Index items by key function (last item wins)."""
    return {key(item): item for item in items}


def chunked(items: list[T], size: int) -> list[list[T]]:
    """Split list into chunks of given size."""
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    return [items[i : i + size] for i in range(0, len(items), size)]


def first_or_none(items: list[T]) -> T | None:
    """Return first item or None."""
    return items[0] if items else None


def last_or_none(items: list[T]) -> T | None:
    """Return last item or None."""
    return items[-1] if items else None


def unique(items: list[T]) -> list[T]:
    """Return unique items preserving order."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def flatten(nested: list[list[T]]) -> list[T]:
    """Flatten a list of lists."""
    return [item for sublist in nested for item in sublist]


def partition(items: list[T], predicate: Callable[[T], bool]) -> tuple[list[T], list[T]]:
    """Partition items based on predicate."""
    true_items = []
    false_items = []
    for item in items:
        if predicate(item):
            true_items.append(item)
        else:
            false_items.append(item)
    return true_items, false_items
