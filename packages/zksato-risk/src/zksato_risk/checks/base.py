"""Risk check protocols."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from zksato_core.models import OrderIntent, RiskContext, RiskDecision


class RiskCheck(Protocol):
    """Protocol for risk checks."""

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        """Check risk and return list of rejection reasons (empty if pass)."""
        ...


@dataclass(frozen=True, slots=True)
class BaseRiskCheck:
    """Base class for risk checks."""

    name: str = ""

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        """Check risk and return list of rejection reasons."""
        return []


class CompositeRiskCheck:
    """Composite risk check that runs multiple checks."""

    def __init__(self, checks: list[RiskCheck]) -> None:
        self.checks = checks

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        """Run all checks and combine reasons."""
        all_reasons: list[str] = []
        for check in self.checks:
            reasons = check.check(intent, context)
            all_reasons.extend(reasons)
        return all_reasons