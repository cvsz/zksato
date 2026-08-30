from dataclasses import dataclass, field
from enum import StrEnum

from zksato.domain import Side


class Outcome(StrEnum):
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


@dataclass
class LiquidityPool:
    """Constant-Product Market Maker (CPMM) liquidity pool for binary outcome contracts."""

    up_reserve: float = 5000.0
    down_reserve: float = 5000.0
    k: float = field(init=False)

    def __post_init__(self) -> None:
        self.k = self.up_reserve * self.down_reserve

    @property
    def spot_up_price(self) -> float:
        total = self.up_reserve + self.down_reserve
        return self.up_reserve / total if total > 0 else 0.5

    @property
    def spot_down_price(self) -> float:
        total = self.up_reserve + self.down_reserve
        return self.down_reserve / total if total > 0 else 0.5

    def quote_buy(self, side: Side, usd_amount: float) -> tuple[float, float, float]:
        """Calculates (shares_out, execution_price, slippage_bps) for a buy order."""
        if usd_amount <= 0:
            return 0.0, 0.5, 0.0

        spot_p = self.spot_up_price if side == Side.UP else self.spot_down_price
        # Linear + quadratic liquidity depth price impact approximation
        depth_usd = (self.up_reserve + self.down_reserve) * 0.5
        impact = usd_amount / depth_usd if depth_usd > 0 else 0.01
        exec_price = min(0.99, spot_p * (1.0 + impact * 0.5))
        shares_out = usd_amount / exec_price if exec_price > 0 else 0.0
        slippage_bps = max(0.0, (exec_price - spot_p) / spot_p * 10_000)
        return shares_out, exec_price, slippage_bps

    def swap_buy(self, side: Side, usd_amount: float) -> tuple[float, float, float]:
        """Executes a buy swap, mutating pool reserves."""
        shares_out, exec_price, slippage_bps = self.quote_buy(side, usd_amount)
        if side == Side.UP:
            self.up_reserve += usd_amount
        else:
            self.down_reserve += usd_amount
        self.k = self.up_reserve * self.down_reserve
        return shares_out, exec_price, slippage_bps


@dataclass(frozen=True)
class RiskLimits:
    max_order_usd: float = 10.0
    max_market_exposure_usd: float = 100.0
    max_directional_shares: float = 100.0
    daily_loss_limit_usd: float = 25.0
    min_edge: float = 0.03
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
    max_slippage_bps: float = 500.0

