"""Hook system for trading scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class HookType(str, Enum):
    """Types of trading hooks."""
    PRE_RISK_CHECK = "pre_risk_check"
    POST_RISK_CHECK = "post_risk_check"
    PRE_ORDER_PLACE = "pre_order_place"
    POST_ORDER_PLACE = "post_order_place"
    ON_FILL = "on_fill"
    ON_REJECT = "on_reject"
    ON_RECONCILIATION_DRIFT = "on_reconciliation_drift"
    ON_RISK_LIMIT_BREACH = "on_risk_limit_breach"
    ON_KILL_SWITCH = "on_kill_switch"
    PRE_TOOL_EXECUTE = "pre_tool_execute"
    POST_TOOL_EXECUTE = "post_tool_execute"
    ON_ERROR = "on_error"


@dataclass
class HookManager:
    """Manages trading lifecycle hooks."""
    
    _hooks: dict[HookType, list[Callable]] = field(default_factory=dict)
    
    def register(self, hook_type: HookType, fn: Callable) -> None:
        """Register a hook function."""
        if hook_type not in self._hooks:
            self._hooks[hook_type] = []
        self._hooks[hook_type].append(fn)
    
    def unregister(self, hook_type: HookType, fn: Callable) -> bool:
        """Unregister a hook function."""
        if hook_type in self._hooks and fn in self._hooks[hook_type]:
            self._hooks[hook_type].remove(fn)
            return True
        return False
    
    async def run(self, hook_type: HookType, *args, **kwargs) -> list[Any]:
        """Run all hooks of a given type."""
        results = []
        for hook in self._hooks.get(hook_type, []):
            try:
                result = await hook(*args, **kwargs)
                results.append(result)
            except Exception as e:
                # Log error in production
                results.append({"error": str(e)})
        return results
    
    def list_hooks(self, hook_type: HookType | None = None) -> dict[str, list[str]]:
        """List registered hooks."""
        if hook_type:
            return {hook_type.value: [h.__name__ for h in self._hooks.get(hook_type, [])]}
        return {ht.value: [h.__name__ for h in fns] for ht, fns in self._hooks.items()}