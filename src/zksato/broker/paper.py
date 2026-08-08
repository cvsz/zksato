from __future__ import annotations

from zksato.domain import OrderIntent, OrderRecord, OrderStatus


class PaperBroker:
    """In-memory execution adapter used by default.

    It never sends orders to an external broker. The adapter deliberately records an
    accepted order only; fill simulation is a separate concern for the backtest/paper
    execution phase.
    """

    def __init__(self) -> None:
        self._orders: list[OrderRecord] = []
        self._client_order_ids: set[str] = set()

    async def place_order(self, intent: OrderIntent) -> OrderRecord:
        if intent.client_order_id and intent.client_order_id in self._client_order_ids:
            raise ValueError("duplicate client_order_id")

        order = OrderRecord(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            order_type=intent.order_type,
            price=intent.price,
            status=OrderStatus.ACCEPTED,
        )
        self._orders.append(order)
        if intent.client_order_id:
            self._client_order_ids.add(intent.client_order_id)
        return order

    async def list_orders(self) -> list[OrderRecord]:
        return list(self._orders)
