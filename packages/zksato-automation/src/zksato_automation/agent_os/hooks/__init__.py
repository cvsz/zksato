"""Hooks system for ZKSATO agent orchestration.

Provides a typed lifecycle event framework for agent orchestration.
"""

from .framework import (
    HookContext,
    HookEvent,
    HookManager,
    HookPriority,
    HookRegistration,
    HookResult,
    setup_builtin_hooks,
)

__all__ = [
    "HookContext",
    "HookEvent",
    "HookManager",
    "HookPriority",
    "HookRegistration",
    "HookResult",
    "setup_builtin_hooks",
]
