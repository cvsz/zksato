"""Plugin registry for strategies, indicators, and brokers."""

from __future__ import annotations

import importlib.metadata
from typing import Any, Protocol

from zksato_core.models import StrategyConfig

from zksato_strategy.strategies.classic import StrategyEngine


class StrategyPlugin(Protocol):
    """Protocol for strategy plugins."""

    name: str
    version: str
    description: str
    parameter_space: dict[str, Any]

    def create_strategy(self, config: StrategyConfig) -> StrategyEngine: ...


class IndicatorPlugin(Protocol):
    """Protocol for indicator plugins."""

    name: str
    version: str
    description: str
    function: Any


class PluginRegistry:
    """Registry for strategy and indicator plugins."""

    def __init__(self) -> None:
        self.strategies: dict[str, StrategyPlugin] = {}
        self.indicators: dict[str, IndicatorPlugin] = {}
        self._discovered = False

    def register_strategy(self, plugin: StrategyPlugin) -> None:
        """Register a strategy plugin."""
        self.strategies[plugin.name] = plugin

    def register_indicator(self, plugin: IndicatorPlugin) -> None:
        """Register an indicator plugin."""
        self.indicators[plugin.name] = plugin

    def get_strategy(self, name: str) -> StrategyPlugin | None:
        """Get a strategy plugin by name."""
        return self.strategies.get(name)

    def get_indicator(self, name: str) -> IndicatorPlugin | None:
        """Get an indicator plugin by name."""
        return self.indicators.get(name)

    def list_strategies(self) -> list[dict[str, str]]:
        """List all registered strategies."""
        return [
            {"name": p.name, "version": p.version, "description": p.description}
            for p in self.strategies.values()
        ]

    def list_indicators(self) -> list[dict[str, str]]:
        """List all registered indicators."""
        return [
            {"name": p.name, "version": p.version, "description": p.description}
            for p in self.indicators.values()
        ]

    def discover(self) -> None:
        """Discover plugins from entry points."""
        if self._discovered:
            return

        # Discover strategy plugins
        for ep in importlib.metadata.entry_points(group="zksato.strategies"):
            try:
                plugin = ep.load()
                self.register_strategy(plugin)
            except Exception:
                pass  # Log error in production

        # Discover indicator plugins
        for ep in importlib.metadata.entry_points(group="zksato.indicators"):
            try:
                plugin = ep.load()
                self.register_indicator(plugin)
            except Exception:
                pass

        self._discovered = True

    def create_strategy(self, name: str, config: StrategyConfig) -> StrategyEngine:
        """Create a strategy instance from a plugin."""
        plugin = self.get_strategy(name)
        if plugin is None:
            # Fall back to built-in
            return StrategyEngine()
        return plugin.create_strategy(config)


# Global registry instance
_global_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
        _global_registry.discover()
    return _global_registry
