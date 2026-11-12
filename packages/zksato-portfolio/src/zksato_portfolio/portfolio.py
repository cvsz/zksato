"""Portfolio management for zksato."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from zksato_core.types import Side
from zksato_core.models import Position, PortfolioSnapshot, OrderRecord


@dataclass
class PortfolioManager:
    """Manages portfolio state and positions."""
    
    initial_cash: float = 500_000.0
    _cash: Decimal = field(init=False, default=Decimal("0"))
    _positions: dict[str, Position] = field(init=False, default_factory=dict)
    _realized_pnl: Decimal = field(init=False, default=Decimal("0"))
    _trade_history: list[dict] = field(init=False, default_factory=list)
    
    def __post_init__(self) -> None:
        self._cash = Decimal(str(self.initial_cash))
    
    @property
    def cash(self) -> float:
        return float(self._cash)
    
    @property
    def positions(self) -> dict[str, Position]:
        return self._positions
    
    @property
    def realized_pnl(self) -> float:
        return float(self._realized_pnl)
    
    async def apply_fill(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        price: float,
        fill_id: str,
        commission: float = 0.0,
    ) -> Position:
        """Apply a fill to the portfolio."""
        quantity_dec = Decimal(str(quantity))
        price_dec = Decimal(str(price))
        commission_dec = Decimal(str(commission))
        cost = quantity_dec * price_dec + commission_dec
        
        if side == Side.BUY:
            if self._cash < cost:
                raise ValueError(f"Insufficient cash: {self._cash} < {cost}")
            self._cash -= cost
            
            if symbol in self._positions:
                pos = self._positions[symbol]
                total_qty = pos.quantity + quantity_dec
                total_cost = pos.average_price * pos.quantity + price_dec * quantity_dec
                pos.average_price = total_cost / total_qty
                pos.quantity = total_qty
                pos.cost_value = total_cost
            else:
                self._positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity_dec,
                    average_price=price_dec,
                    market_price=price_dec,
                    market_value=cost,
                    cost_value=cost,
                    unrealized_pnl=Decimal("0"),
                    unrealized_pnl_pct=Decimal("0"),
                )
        
        elif side == Side.SELL:
            if symbol not in self._positions:
                raise ValueError(f"No position to sell for {symbol}")
            
            pos = self._positions[symbol]
            if pos.quantity < quantity_dec:
                raise ValueError(f"Insufficient position: {pos.quantity} < {quantity_dec}")
            
            self._cash += price_dec * quantity_dec - commission_dec
            realized = (price_dec - pos.average_price) * quantity_dec - commission_dec
            self._realized_pnl += realized
            pos.quantity -= quantity_dec
            
            if pos.quantity == 0:
                del self._positions[symbol]
        
        self._trade_history.append({
            "fill_id": fill_id,
            "symbol": symbol,
            "side": side.value,
            "quantity": float(quantity_dec),
            "price": float(price_dec),
            "commission": float(commission_dec),
            "timestamp": datetime.now(UTC).isoformat(),
        })
        
        return self._positions.get(symbol)
    
    async def update_market_price(self, symbol: str, price: float) -> None:
        """Update market price for a position."""
        if symbol in self._positions:
            pos = self._positions[symbol]
            price_dec = Decimal(str(price))
            pos.market_price = price_dec
            pos.market_value = pos.quantity * price_dec
            pos.unrealized_pnl = pos.market_value - pos.cost_value
            if pos.cost_value > 0:
                pos.unrealized_pnl_pct = (pos.unrealized_pnl / pos.cost_value) * Decimal("100")
    
    async def snapshot(self) -> PortfolioSnapshot:
        """Get portfolio snapshot."""
        market_value = sum(pos.market_value for pos in self._positions.values())
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self._positions.values())
        equity = self._cash + market_value
        
        return PortfolioSnapshot(
            cash=float(self._cash),
            market_value=float(market_value),
            equity=float(equity),
            realized_pnl=float(self._realized_pnl),
            unrealized_pnl=float(unrealized_pnl),
            daily_pnl=0.0,
            positions=list(self._positions.values()),
        )
    
    async def get_position(self, symbol: str) -> Position | None:
        """Get position for a symbol."""
        return self._positions.get(symbol)
    
    async def close_position(self, symbol: str, price: float) -> Position | None:
        """Close a position entirely."""
        if symbol not in self._positions:
            return None
        
        pos = self._positions[symbol]
        side = Side.SELL if pos.quantity > 0 else Side.BUY
        await self.apply_fill(symbol, side, abs(float(pos.quantity)), price, f"close_{symbol}")
        return pos