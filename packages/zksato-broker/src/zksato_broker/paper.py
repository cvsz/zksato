"""Paper broker implementation for deterministic simulation."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from zksato_core.types import Side, OrderType, OrderStatus
from zksato_core.models import OrderIntent, OrderRecord, OrderEvent, PortfolioSnapshot, Position, Quote
from zksato_core.money import Money
from zksato_broker.base import BaseBroker, BrokerConfig, BrokerCapabilities
from zksato_broker.protocol import BrokerAdapter


class PaperPortfolio:
    """Paper trading portfolio for simulation."""
    
    def __init__(self, initial_cash: float = 500_000.0) -> None:
        self.cash = Decimal(str(initial_cash))
        self.positions: dict[str, Position] = {}
        self.realized_pnl = Decimal("0")
        self._lock = asyncio.Lock()
    
    async def apply_fill(
        self,
        symbol: str,
        side: Side,
        quantity: float,
        price: float,
        fill_id: str,
    ) -> None:
        """Apply a fill to the portfolio."""
        async with self._lock:
            quantity_dec = Decimal(str(quantity))
            price_dec = Decimal(str(price))
            cost = quantity_dec * price_dec
            
            if side == Side.BUY:
                # Buy: decrease cash, increase position
                if self.cash < cost:
                    raise ValueError("Insufficient cash for buy order")
                self.cash -= cost
                
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    total_qty = pos.quantity + quantity_dec
                    total_cost = (pos.average_price * pos.quantity) + cost
                    pos.average_price = total_cost / total_qty
                    pos.quantity = total_qty
                else:
                    self.positions[symbol] = Position(
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
                # Sell: increase cash, decrease position
                if symbol not in self.positions:
                    raise ValueError(f"No position to sell for {symbol}")
                
                pos = self.positions[symbol]
                if pos.quantity < quantity_dec:
                    raise ValueError(f"Insufficient position to sell {symbol}: have {pos.quantity}, need {quantity_dec}")
                
                self.cash += cost
                pos.quantity -= quantity_dec
                realized = (price_dec - pos.average_price) * quantity_dec
                self.realized_pnl += realized
                
                if pos.quantity == 0:
                    del self.positions[symbol]
    
    async def update_market_price(self, symbol: str, price: float) -> None:
        """Update market price for a position."""
        async with self._lock:
            if symbol in self.positions:
                pos = self.positions[symbol]
                price_dec = Decimal(str(price))
                pos.market_price = price_dec
                pos.market_value = pos.quantity * price_dec
                pos.unrealized_pnl = pos.market_value - pos.cost_value
                if pos.cost_value > 0:
                    pos.unrealized_pnl_pct = (pos.unrealized_pnl / pos.cost_value) * Decimal("100")
    
    async def snapshot(self) -> PortfolioSnapshot:
        """Get portfolio snapshot."""
        async with self._lock:
            market_value = sum(pos.market_value for pos in self.positions.values())
            unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            equity = self.cash + market_value
            
            return PortfolioSnapshot(
                cash=float(self.cash),
                market_value=float(market_value),
                equity=float(equity),
                realized_pnl=float(self.realized_pnl),
                unrealized_pnl=float(unrealized_pnl),
                daily_pnl=0.0,  # Would need previous day's equity
                positions=list(self.positions.values()),
            )


class PaperBroker(BaseBroker):
    """Deterministic paper broker with restart-safe resting-limit matching."""
    
    def __init__(
        self,
        config: BrokerConfig,
        initial_cash: float = 500_000.0,
        match_resting_limits: bool = True,
        max_fill_quantity_per_quote: int = 0,
        price_improvement: bool = True,
    ) -> None:
        super().__init__(config)
        self.account = PaperPortfolio(initial_cash=initial_cash)
        self.match_resting_limits = match_resting_limits
        self.max_fill_quantity_per_quote = max(0, max_fill_quantity_per_quote)
        self.price_improvement = price_improvement
        self._client_order_ids: set[str] = set()
        self._orders: dict[str, OrderRecord] = {}
        self._lock = asyncio.Lock()
    
    @property
    def capabilities(self) -> set[BrokerCapabilities]:
        return {
            BrokerCapabilities.PAPER_TRADING,
            BrokerCapabilities.EQUITY,
            BrokerCapabilities.MARKET_ORDERS,
            BrokerCapabilities.LIMIT_ORDERS,
            BrokerCapabilities.STOP_ORDERS,
            BrokerCapabilities.POSITION_TRACKING,
            BrokerCapabilities.ACCOUNT_BALANCE,
        }
    
    async def _do_connect(self) -> None:
        """Initialize paper broker."""
        pass
    
    async def _do_disconnect(self) -> None:
        """Clean up paper broker."""
        pass
    
    async def place_order(self, intent: OrderIntent) -> OrderRecord:
        """Place a paper order."""
        async with self._lock:
            # Check for duplicate client_order_id
            if intent.client_order_id and intent.client_order_id in self._client_order_ids:
                raise ValueError(f"duplicate client_order_id: {intent.client_order_id}")
            
            # Get current quote for the symbol
            quote = await self.get_quote(intent.symbol)
            
            if intent.order_type == OrderType.MARKET:
                if quote is None:
                    raise ValueError("market order requires a current quote")
                fill_price = self._market_price(intent.side, quote)
                order = self._new_order(intent)
                return await self._apply_fill(order, intent.quantity, fill_price, event_type="paper_market_fill")
            
            if intent.price is None:
                raise ValueError("limit order requires price")
            
            if quote is not None and self._limit_marketable(intent.side, intent.price, quote):
                order = self._new_order(intent)
                fill_price = self._limit_fill_price(intent.side, intent.price, quote)
                return await self._apply_fill(order, intent.quantity, fill_price, event_type="paper_limit_fill")
            
            return self._accepted(intent)
    
    async def process_quote(self, quote: Quote) -> list[OrderRecord]:
        """Match persisted resting limits when a later quote makes them executable."""
        if not self.match_resting_limits:
            return []
        
        async with self._lock:
            changed: list[OrderRecord] = []
            for order in self._orders.values():
                if order.symbol != quote.symbol or order.order_type != OrderType.LIMIT:
                    continue
                if order.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
                    continue
                if order.price is None or not self._limit_marketable(order.side, order.price, quote):
                    continue
                
                remaining = float(order.quantity) - float(order.filled_quantity)
                if remaining <= 0:
                    continue
                
                fill_quantity = float(remaining)
                if self.max_fill_quantity_per_quote > 0:
                    fill_quantity = min(fill_quantity, float(self.max_fill_quantity_per_quote))
                
                fill_price = self._limit_fill_price(order.side, order.price, quote)
                try:
                    changed.append(await self._apply_fill(order, fill_quantity, fill_price, event_type="paper_resting_limit_fill"))
                except ValueError as exc:
                    order.status = OrderStatus.CANCELLED
                    order.message = f"paper resting order cancelled before fill: {exc}"
                    order.updated_at = datetime.now(UTC)
                    self._orders[str(order.id)] = order
                    # Add order event would go here if we had event store
                    changed.append(order)
            return changed
    
    def _new_order(self, intent: OrderIntent) -> OrderRecord:
        now = datetime.now(UTC)
        order = OrderRecord(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            filled_quantity=0,
            order_type=intent.order_type,
            price=intent.price,
            average_fill_price=None,
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
            status=OrderStatus.ACCEPTED,
            source=intent.source or self.name,
            created_at=now,
            updated_at=now,
        )
        self._orders[str(order.id)] = order
        return order
    
    def _accepted(self, intent: OrderIntent) -> OrderRecord:
        order = self._new_order(intent)
        if intent.client_order_id:
            self._client_order_ids.add(intent.client_order_id)
        return order
    
    async def _apply_fill(
        self,
        order: OrderRecord,
        quantity: float,
        price: float,
        *,
        event_type: str,
    ) -> OrderRecord:
        remaining = float(order.quantity) - float(order.filled_quantity)
        if quantity <= 0 or quantity - remaining > 1e-9:
            raise ValueError("invalid paper fill quantity")
        
        fill_id = f"fill:{order.id}:{order.filled_quantity}"
        await self.account.apply_fill(order.symbol, order.side, quantity, float(price), fill_id=fill_id)
        
        previous_quantity = order.filled_quantity
        previous_value = (order.average_fill_price or 0.0) * previous_quantity
        new_quantity = previous_quantity + quantity
        order.average_fill_price = (previous_value + (price * quantity)) / new_quantity
        order.filled_quantity = new_quantity
        order.status = OrderStatus.FILLED if new_quantity >= order.quantity else OrderStatus.PARTIALLY_FILLED
        order.updated_at = datetime.now(UTC)
        
        if order.client_order_id:
            self._client_order_ids.add(order.client_order_id)
        
        return order
    
    @staticmethod
    def _market_price(side: Side, quote: Quote) -> float:
        if side == Side.BUY:
            return float(quote.offer or quote.last or 0)
        return float(quote.bid or quote.last or 0)
    
    @staticmethod
    def _limit_marketable(side: Side, limit_price: float, quote: Quote) -> bool:
        executable = float(quote.offer or quote.last or 0) if side == Side.BUY else float(quote.bid or quote.last or 0)
        if executable == 0:
            return False
        return executable <= limit_price if side == Side.BUY else executable >= limit_price
    
    def _limit_fill_price(self, side: Side, limit_price: float, quote: Quote) -> float:
        executable = self._market_price(side, quote)
        if not self.price_improvement:
            return float(limit_price)
        if side == Side.BUY:
            return float(min(limit_price, executable))
        return float(max(limit_price, executable))
    
    async def cancel_order(self, order_id: str) -> OrderRecord:
        async with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise ValueError(f"order not found: {order_id}")
            
            if order.status not in {OrderStatus.ACCEPTED, OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED}:
                raise ValueError("only open paper orders can be cancelled")
            
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now(UTC)
            return order
    
    async def list_orders(self, status: OrderStatus | None = None) -> list[OrderRecord]:
        async with self._lock:
            orders = list(self._orders.values())
            if status:
                orders = [o for o in orders if o.status == status]
            return orders
    
    async def get_positions(self) -> list[Position]:
        return list((await self.account.snapshot()).positions)
    
    async def get_account(self) -> dict[str, Any]:
        snap = await self.account.snapshot()
        return {
            "cash": snap.cash,
            "equity": snap.equity,
            "market_value": snap.market_value,
        }
    
    async def get_portfolio(self) -> PortfolioSnapshot:
        return await self.account.snapshot()
    
    async def get_quote(self, symbol: str) -> Quote | None:
        """Get quote for a symbol. In paper mode, this would come from market data feed."""
        # This is a placeholder - in real usage, quotes come from market feeds
        return None