"""Sub-account management for agent OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from zksato_core.models import PortfolioSnapshot, Position


@dataclass
class Quotas:
    """Resource quotas for a sub-account."""
    max_orders: int = 100
    max_notional: float = 1_000_000.0
    max_positions: int = 10
    max_position_pct: float = 0.2
    allowed_symbols: list[str] = field(default_factory=list)
    allowed_strategies: list[str] = field(default_factory=list)


@dataclass
class SubAccount:
    """Sub-account with isolated quotas and risk limits."""
    
    account_id: str
    parent_id: str
    quotas: Quotas
    session: Any = None  # AgentSession
    _order_count: int = 0
    _total_notional: float = 0.0
    
    def can_execute(self, order_value: float, symbol: str, strategy: str) -> tuple[bool, str]:
        """Check if order can be executed within quotas."""
        if self._order_count >= self.quotas.max_orders:
            return False, f"Order limit reached: {self.quotas.max_orders}"
        
        if self._total_notional + order_value > self.quotas.max_notional:
            return False, f"Notional limit exceeded: {self.quotas.max_notional}"
        
        if self.quotas.allowed_symbols and symbol not in self.quotas.allowed_symbols:
            return False, f"Symbol not allowed: {symbol}"
        
        if self.quotas.allowed_strategies and strategy not in self.quotas.allowed_strategies:
            return False, f"Strategy not allowed: {strategy}"
        
        return True, "OK"
    
    def record_order(self, order_value: float) -> None:
        """Record an executed order."""
        self._order_count += 1
        self._total_notional += order_value
    
    def get_usage(self) -> dict[str, Any]:
        """Get current usage statistics."""
        return {
            "orders": self._order_count,
            "notional": self._total_notional,
            "quotas": {
                "max_orders": self.quotas.max_orders,
                "max_notional": self.quotas.max_notional,
                "max_positions": self.quotas.max_positions,
            },
        }