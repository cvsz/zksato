from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from zksato.config import get_settings
from zksato.domain import (
    OrderEvent,
    OrderIntent,
    OrderRecord,
    OrderStatus,
    OrderType,
    PortfolioSnapshot,
    Quote,
    Side,
)
from zksato.portfolio import PaperPortfolio
from zksato.store import StateStore


class PaperBroker:
    """Deterministic paper broker with restart-safe resting-limit matching."""

    def __init__(
        self,
        store: StateStore,
        initial_cash: float = 500_000.0,
        *,
        match_resting_limits: bool | None = None,
        max_fill_quantity_per_quote: int | None = None,
        price_improvement: bool | None = None,
    ) -> None:
        settings = get_settings()
        self.store = store
        self.account = PaperPortfolio(store=store, initial_cash=initial_cash)
        self.match_resting_limits = (
            settings.paper_match_resting_limits
            if match_resting_limits is None
            else match_resting_limits
        )
        self.max_fill_quantity_per_quote = max(
            0,
            settings.paper_max_fill_quantity_per_quote
            if max_fill_quantity_per_quote is None
            else max_fill_quantity_per_quote,
        )
        self.price_improvement = (
            settings.paper_price_improvement if price_improvement is None else price_improvement
        )
        self._client_order_ids: set[str] = {
            order.client_order_id
            for order in store.list_orders()
            if order.client_order_id is not None
        }
        self._lock = asyncio.Lock()

    async def place_order(self, intent: OrderIntent) -> OrderRecord:
        if intent.client_order_id and intent.client_order_id in self._client_order_ids:
            raise ValueError("duplicate client_order_id")

        quote = self.store.get_quote(intent.symbol)
        if intent.order_type == OrderType.MARKET:
            if quote is None:
                raise ValueError("market order requires a current quote")
            fill_price = self._market_price(intent.side, quote)
            order = self._new_order(intent)
            return self._apply_fill(
                order, intent.quantity, fill_price, event_type="paper_market_fill"
            )

        if intent.price is None:
            raise ValueError("limit order requires price")
        if quote is not None and self._limit_marketable(intent.side, intent.price, quote):
            order = self._new_order(intent)
            fill_price = self._limit_fill_price(intent.side, intent.price, quote)
            return self._apply_fill(
                order, intent.quantity, fill_price, event_type="paper_limit_fill"
            )
        return self._accepted(intent)

    async def process_quote(self, quote: Quote) -> list[OrderRecord]:
        """Match persisted resting limits when a later quote makes them executable."""

        if not self.match_resting_limits:
            return []
        async with self._lock:
            changed: list[OrderRecord] = []
            for order in self.store.list_orders():
                if order.symbol != quote.symbol or order.order_type != OrderType.LIMIT:
                    continue
                if order.status not in {OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}:
                    continue
                if order.price is None or not self._limit_marketable(
                    order.side, order.price, quote
                ):
                    continue
                remaining = max(float(order.quantity) - float(order.filled_quantity), 0)
                if remaining <= 0:
                    continue
                fill_quantity = float(remaining)
                if self.max_fill_quantity_per_quote > 0:
                    fill_quantity = min(
                        float(fill_quantity),
                        float(self.max_fill_quantity_per_quote),
                    )
                fill_price = self._limit_fill_price(order.side, order.price, quote)
                try:
                    changed.append(
                        self._apply_fill(
                            order,
                            float(fill_quantity),
                            fill_price,
                            event_type="paper_resting_limit_fill",
                        )
                    )
                except ValueError as exc:
                    order.status = OrderStatus.CANCELLED
                    order.message = f"paper resting order cancelled before fill: {exc}"
                    order.updated_at = datetime.now(UTC)
                    self.store.upsert_order(order)
                    self.store.add_order_event(
                        OrderEvent(
                            order_id=order.id,
                            event_type="paper_resting_limit_cancelled",
                            status=order.status,
                            data={"reason": str(exc)},
                        )
                    )
                    self.store.add_audit(
                        "order.paper_cancelled",
                        order.message,
                        {"order_id": str(order.id), "symbol": order.symbol},
                    )
                    changed.append(order)
            return changed

    def _new_order(self, intent: OrderIntent) -> OrderRecord:
        now = datetime.now(UTC)
        return OrderRecord(
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
            source=intent.source,
            created_at=now,
            updated_at=now,
        )

    def _accepted(self, intent: OrderIntent) -> OrderRecord:
        order = self._new_order(intent)
        self.store.upsert_order(order)
        if intent.client_order_id:
            self._client_order_ids.add(intent.client_order_id)
        self.store.add_order_event(
            OrderEvent(
                order_id=order.id,
                event_type="paper_order_accepted",
                status=order.status,
                data={"price": order.price or 0.0},
            )
        )
        return order

    def _apply_fill(
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
        self.account.apply_fill(order.symbol, order.side, quantity, float(price))
        previous_quantity = order.filled_quantity
        previous_value = (order.average_fill_price or 0.0) * previous_quantity
        new_quantity = previous_quantity + quantity
        order.average_fill_price = (previous_value + (price * quantity)) / new_quantity
        order.filled_quantity = new_quantity
        order.status = (
            OrderStatus.FILLED if new_quantity >= order.quantity else OrderStatus.PARTIALLY_FILLED
        )
        order.updated_at = datetime.now(UTC)
        self.store.upsert_order(order)
        self.store.record_order_fill(order, source="paper")
        if order.client_order_id:
            self._client_order_ids.add(order.client_order_id)
        self.store.add_order_event(
            OrderEvent(
                order_id=order.id,
                event_type=event_type,
                status=order.status,
                data={
                    "fill_quantity": quantity,
                    "filled_quantity": order.filled_quantity,
                    "fill_price": price,
                },
            )
        )
        self.store.add_audit(
            "order.filled" if order.status == OrderStatus.FILLED else "order.partially_filled",
            (
                f"paper {order.side.value} {quantity} {order.symbol} @ {price:.2f} "
                f"({order.filled_quantity}/{order.quantity})"
            ),
            {"order_id": str(order.id), "source": order.source},
        )
        return order

    @staticmethod
    def _market_price(side: Side, quote: Quote) -> float:
        return float((quote.offer or quote.last) if side == Side.BUY else (quote.bid or quote.last))

    @staticmethod
    def _limit_marketable(side: Side, limit_price: float, quote: Quote) -> bool:
        executable = (quote.offer or quote.last) if side == Side.BUY else (quote.bid or quote.last)
        return executable <= limit_price if side == Side.BUY else executable >= limit_price

    def _limit_fill_price(self, side: Side, limit_price: float, quote: Quote) -> float:
        executable = self._market_price(side, quote)
        if not self.price_improvement:
            return float(limit_price)
        if side == Side.BUY:
            return float(min(limit_price, executable))
        return float(max(limit_price, executable))

    async def cancel_order(self, order_id: str) -> OrderRecord:
        for order in self.store.list_orders():
            if str(order.id) == order_id:
                if order.status not in {
                    OrderStatus.ACCEPTED,
                    OrderStatus.PENDING,
                    OrderStatus.PARTIALLY_FILLED,
                }:
                    raise ValueError("only open paper orders can be cancelled")
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now(UTC)
                self.store.upsert_order(order)
                self.store.add_order_event(
                    OrderEvent(
                        order_id=order.id,
                        event_type="paper_order_cancelled",
                        status=order.status,
                        data={"filled_quantity": order.filled_quantity},
                    )
                )
                self.store.add_audit("order.cancelled", f"cancelled paper order {order_id}")
                return order
        raise ValueError("order not found")

    async def list_orders(self) -> list[OrderRecord]:
        return self.store.list_orders()

    async def portfolio(self) -> PortfolioSnapshot:
        return self.account.snapshot()
