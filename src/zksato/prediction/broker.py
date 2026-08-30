from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zksato.config import Settings
from zksato.domain import Side
from zksato.prediction.core import LiquidityPool, Position, RiskLimits


class RiskRejected(RuntimeError):
    pass


@dataclass(frozen=True)
class Fill:
    side: Side
    shares: float
    price: float
    total_cost: float


class PaperPredictionBroker:
    """Deterministic paper broker for prediction markets."""

    def __init__(
        self,
        settings: Settings,
        limits: RiskLimits | None = None,
        pool: LiquidityPool | None = None,
    ) -> None:
        self.settings = settings
        self.limits = limits or RiskLimits()
        self.pool = pool
        self.starting_cash = 10_000.0
        self.cash = self.starting_cash
        self.position = Position()
        self.fills: list[Fill] = []
        self._orders: dict[str, dict[str, Any]] = {}

    def execute(self, side: Side, quoted_price: float, order_usd: float) -> Fill:
        if not 0.0 < quoted_price < 1.0:
            raise RiskRejected("price must be between 0 and 1")
        if order_usd <= 0 or order_usd > self.limits.max_order_usd:
            raise RiskRejected("order exceeds configured order limit")

        if self.pool is not None:
            shares, price, slippage_bps = self.pool.swap_buy(side, order_usd)
            if slippage_bps > self.limits.max_slippage_bps:
                raise RiskRejected(f"slippage {slippage_bps:.1f} bps exceeds limit")
        else:
            slippage = quoted_price * self.limits.slippage_bps / 10_000
            price = min(0.999999, quoted_price + slippage)
            shares = order_usd / price

        fee = order_usd * self.limits.fee_bps / 10_000
        total = order_usd + fee
        if total > self.cash:
            raise RiskRejected("insufficient paper cash")
        if self.position.gross_exposure + total > self.limits.max_market_exposure_usd:
            raise RiskRejected("market exposure limit reached")
        shares = order_usd / price
        projected = dict(self.position.shares)
        projected[side] += shares
        if abs(projected[Side.UP] - projected[Side.DOWN]) > self.limits.max_directional_shares:
            raise RiskRejected("directional residual limit reached")
        self.cash -= total
        self.position.shares[side] += shares
        self.position.cost[side] += total
        fill = Fill(side, shares, price, total)
        self.fills.append(fill)
        return fill

    async def create_order(
        self, market_id: str, side: str, amount_usd: float, price: float
    ) -> dict[str, Any]:
        try:
            normalized_side = Side(side.lower())
        except ValueError as exc:
            raise ValueError(f"unsupported prediction side: {side}") from exc
        if normalized_side not in {Side.UP, Side.DOWN}:
            raise ValueError(f"unsupported prediction side: {side}")
        fill = self.execute(normalized_side, price, amount_usd)
        order_id = f"paper-{len(self.fills)}"
        payload: dict[str, Any] = {
            "id": order_id,
            "market_id": market_id,
            "side": fill.side.value,
            "amount": amount_usd / price,
            "price": fill.price,
            "status": "filled",
        }
        self._orders[order_id] = payload
        return dict(payload)

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        payload = self._orders.get(order_id)
        if payload is None:
            raise ValueError("paper prediction order not found")
        cancelled = dict(payload)
        cancelled["status"] = "canceled"
        return cancelled

    async def fetch_open_orders(self, market_id: str) -> list[dict[str, Any]]:
        return [
            dict(payload)
            for payload in self._orders.values()
            if payload.get("market_id") == market_id and payload.get("status") == "open"
        ]

    async def fetch_balance(self) -> dict[str, Any]:
        return {"cash": self.cash}

    def settle(self, winner: Side) -> float:
        payout = self.position.shares[winner]
        self.cash += payout
        pnl = self.cash - self.starting_cash
        return pnl
