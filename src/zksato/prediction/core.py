from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from zksato.domain import Side


class Outcome(str, Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class Tick:
    timestamp: int
    spot: float
    reference: float
    up_ask: float
    down_ask: float
    volatility: float = 0.0
    momentum: float = 0.0


@dataclass
class Signal:
    side: Side
    probability: float
    market_price: float
    edge: float


@dataclass
class Position:
    shares: dict[Side, float] = field(default_factory=lambda: {Side.UP: 0.0, Side.DOWN: 0.0})
    cost: dict[Side, float] = field(default_factory=lambda: {Side.UP: 0.0, Side.DOWN: 0.0})

    @property
    def gross_exposure(self) -> float:
        return sum(self.cost.values())

    @property
    def directional_residual(self) -> float:
        return abs(self.shares[Side.UP] - self.shares[Side.DOWN])


@dataclass(frozen=True)
class RiskLimits:
    max_order_usd: float = 10.0
    max_market_exposure_usd: float = 100.0
    max_directional_shares: float = 100.0
    daily_loss_limit_usd: float = 25.0
    min_edge: float = 0.03
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
