"""Policy registry and discovery."""

from __future__ import annotations

from zksato_risk.policies.base import Policy, PolicyEngine, PolicyRegistry

# Global registry instance
_global_registry = PolicyRegistry()


def get_registry() -> PolicyRegistry:
    """Get the global policy registry."""
    return _global_registry


def register_policy(policy: Policy) -> None:
    """Register a policy in the global registry."""
    _global_registry.register(policy)


def create_policy_engine() -> PolicyEngine:
    """Create a policy engine with all registered policies."""
    return PolicyEngine(_global_registry.get_all())


def discover_policies(module_name: str) -> list[Policy]:
    """Discover policies in a module."""
    import importlib
    import inspect

    module = importlib.import_module(module_name)
    policies = []

    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, Policy) and obj is not Policy:
            try:
                policy = obj()
                policies.append(policy)
            except Exception:
                pass

    return policies
