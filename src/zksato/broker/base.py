from __future__ import annotations

from typing import Protocol

from zksato.domain import OrderIntent, OrderRecord, PortfolioSnapshot


class Broker(Protocol):
    async def place_order(self, intent: OrderIntent) -> OrderRecord: ...

    async def cancel_order(self, order_id: str) -> OrderRecord: ...

    async def list_orders(self) -> list[OrderRecord]: ...

    async def portfolio(self) -> PortfolioSnapshot: ...
