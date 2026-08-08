from __future__ import annotations

from datetime import UTC, datetime

from zksato.domain import OrderIntent, OrderRecord, OrderStatus, OrderType, PortfolioSnapshot
from zksato.portfolio import PaperPortfolio
from zksato.store import StateStore


class PaperBroker:
    """Deterministic in-memory broker with immediate fill simulation."""

    def __init__(self, store: StateStore, initial_cash: float = 500_000.0) -> None:
        self.store = store
        self.account = PaperPortfolio(store=store, initial_cash=initial_cash)
        self._client_order_ids: set[str] = set()

    async def place_order(self, intent: OrderIntent) -> OrderRecord:
        if intent.client_order_id and intent.client_order_id in self._client_order_ids:
            raise ValueError("duplicate client_order_id")

        quote = self.store.get_quote(intent.symbol)
        if intent.order_type == OrderType.MARKET:
            if quote is None:
                raise ValueError("market order requires a current quote")
            fill_price = quote.offer or quote.last if intent.side.value == "buy" else quote.bid or quote.last
        else:
            if intent.price is None:
                raise ValueError("limit order requires price")
            fill_price = intent.price
            if quote is not None:
                if intent.side.value == "buy" and intent.price < (quote.offer or quote.last):
                    return self._accepted(intent)
                if intent.side.value == "sell" and intent.price > (quote.bid or quote.last):
                    return self._accepted(intent)

        self.account.apply_fill(intent.symbol, intent.side, intent.quantity, float(fill_price))
        now = datetime.now(UTC)
        order = OrderRecord(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            filled_quantity=intent.quantity,
            order_type=intent.order_type,
            price=intent.price,
            average_fill_price=float(fill_price),
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
            status=OrderStatus.FILLED,
            source=intent.source,
            created_at=now,
            updated_at=now,
        )
        self.store.add_order(order)
        if intent.client_order_id:
            self._client_order_ids.add(intent.client_order_id)
        self.store.add_audit(
            "order.filled",
            f"paper {intent.side.value} {intent.quantity} {intent.symbol} @ {fill_price:.2f}",
            {"order_id": str(order.id), "source": intent.source},
        )
        return order

    def _accepted(self, intent: OrderIntent) -> OrderRecord:
        order = OrderRecord(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            order_type=intent.order_type,
            price=intent.price,
            stop_loss=intent.stop_loss,
            take_profit=intent.take_profit,
            status=OrderStatus.ACCEPTED,
            source=intent.source,
        )
        self.store.add_order(order)
        if intent.client_order_id:
            self._client_order_ids.add(intent.client_order_id)
        return order

    async def cancel_order(self, order_id: str) -> OrderRecord:
        for order in self.store.orders:
            if str(order.id) == order_id:
                if order.status not in {OrderStatus.ACCEPTED, OrderStatus.PENDING}:
                    raise ValueError("only open paper orders can be cancelled")
                order.status = OrderStatus.CANCELLED
                order.updated_at = datetime.now(UTC)
                self.store.add_audit("order.cancelled", f"cancelled paper order {order_id}")
                return order
        raise ValueError("order not found")

    async def list_orders(self) -> list[OrderRecord]:
        return self.store.list_orders()

    async def portfolio(self) -> PortfolioSnapshot:
        return self.account.snapshot()
