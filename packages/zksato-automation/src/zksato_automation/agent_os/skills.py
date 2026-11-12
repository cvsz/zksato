"""Skill registry for agent OS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from zksato_core.models import Signal, OrderRecord, Position, PortfolioSnapshot
from zksato_core.types import Side


class TradingSkill(Protocol):
    """Protocol for trading skills."""
    name: str
    description: str
    required_capabilities: set[str]
    
    async def execute(self, params: Any, ctx: "SkillContext") -> "SkillResult": ...


@dataclass
class SkillContext:
    """Context for skill execution."""
    account_id: str
    subaccount_id: str | None = None


@dataclass
class SkillResult:
    """Result of skill execution."""
    success: bool
    data: Any = None
    error: str | None = None


@dataclass
class SkillRegistry:
    """Registry for trading skills."""
    
    _skills: dict[str, TradingSkill] = None
    
    def __post_init__(self):
        if self._skills is None:
            self._skills = {}
    
    def register(self, skill: TradingSkill) -> None:
        """Register a skill."""
        self._skills[skill.name] = skill
    
    def get(self, name: str) -> TradingSkill | None:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def list_skills(self) -> list[dict[str, str]]:
        """List all skills."""
        return [
            {"name": s.name, "description": s.description}
            for s in self._skills.values()
        ]


# Built-in skills
class GetQuoteSkill:
    name = "get_quote"
    description = "Get real-time quote for a symbol"
    required_capabilities = {"realtime_quotes"}
    
    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        symbol = params.get("symbol")
        if not symbol:
            return SkillResult(success=False, error="symbol required")
        # Would call market data feed
        return SkillResult(success=True, data={"symbol": symbol, "price": 100.0})


class PlaceOrderSkill:
    name = "place_order"
    description = "Place a trading order"
    required_capabilities = {"order_management"}
    
    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        symbol = params.get("symbol")
        side = params.get("side")
        quantity = params.get("quantity")
        if not all([symbol, side, quantity]):
            return SkillResult(success=False, error="symbol, side, quantity required")
        # Would call broker adapter
        return SkillResult(success=True, data={"order_id": "simulated", "symbol": symbol})


class GetPositionsSkill:
    name = "get_positions"
    description = "Get current positions"
    required_capabilities = {"position_tracking"}
    
    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        # Would call portfolio manager
        return SkillResult(success=True, data={"positions": []})


class CancelOrderSkill:
    name = "cancel_order"
    description = "Cancel an order"
    required_capabilities = {"order_management"}
    
    async def execute(self, params: dict, ctx: SkillContext) -> SkillResult:
        order_id = params.get("order_id")
        if not order_id:
            return SkillResult(success=False, error="order_id required")
        return SkillResult(success=True, data={"cancelled": True, "order_id": order_id})