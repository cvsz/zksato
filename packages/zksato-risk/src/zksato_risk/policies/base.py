"""Policy base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

from zksato_core.models import OrderIntent, RiskContext, RiskDecision

T = TypeVar("T")


class PolicyDecision(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True, slots=True)
class PolicyResult:
    """Result of a policy evaluation."""

    decision: PolicyDecision
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Policy(ABC, Generic[T]):
    """Base class for risk policies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Policy name."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Policy version."""
        ...

    @abstractmethod
    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        """Evaluate the policy against an order intent."""
        ...


class PolicyEngine:
    """Engine for evaluating multiple policies."""

    def __init__(self, policies: list[Policy] | None = None) -> None:
        self.policies = policies or []

    def add_policy(self, policy: Policy) -> None:
        """Add a policy to the engine."""
        self.policies.append(policy)

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> RiskDecision:
        """Evaluate all policies and combine results."""
        all_reasons: list[str] = []
        approved = True
        estimated_notional = 0.0
        estimated_risk_pct: float | None = None

        if context.reference_price:
            estimated_notional = float(context.reference_price * intent.quantity)

        for policy in self.policies:
            result = policy.evaluate(intent, context)
            if (
                result.decision == PolicyDecision.REJECT
                or result.decision == PolicyDecision.REQUIRE_APPROVAL
            ):
                approved = False
                all_reasons.extend(result.reasons)

        return RiskDecision(
            approved=approved,
            reasons=all_reasons,
            estimated_notional=estimated_notional,
            estimated_risk_pct=estimated_risk_pct,
        )


class PolicyRegistry:
    """Registry for managing policies."""

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}

    def register(self, policy: Policy) -> None:
        """Register a policy."""
        self._policies[policy.name] = policy

    def unregister(self, name: str) -> bool:
        """Unregister a policy by name."""
        if name in self._policies:
            del self._policies[name]
            return True
        return False

    def get(self, name: str) -> Policy | None:
        """Get a policy by name."""
        return self._policies.get(name)

    def get_all(self) -> list[Policy]:
        """Get all registered policies."""
        return list(self._policies.values())

    def get_by_type(self, policy_type: type) -> list[Policy]:
        """Get all policies of a specific type."""
        return [p for p in self._policies.values() if isinstance(p, policy_type)]
