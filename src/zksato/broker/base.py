from __future__ import annotations

from typing import Protocol

from zksato.domain import OrderIntent, OrderRecord


class Broker(Protocol):
    async def place_order(self, intent: OrderIntent) -> OrderRecord: ...

    async def list_orders(self) -> list[OrderRecord]: ...
