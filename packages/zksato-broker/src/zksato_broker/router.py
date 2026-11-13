"""Broker router for multi-broker failover."""

from __future__ import annotations

from typing import Any

from zksato_core.models import OrderIntent, OrderRecord
from zksato_core.types import OrderType

from zksato_broker.errors import BrokerError, BrokerErrorCategory, classify_error
from zksato_broker.protocol import BrokerAdapter, BrokerCapabilities


class BrokerUnavailable(Exception):
    """Raised when no broker is available for an order."""

    pass


class BrokerRouter:
    """Routes orders to brokers with failover support.

    Supports:
    - Primary/fallback broker configuration
    - Capability-based routing
    - Automatic failover on transient errors
    - Health-based broker selection
    """

    def __init__(self, brokers: list[BrokerAdapter]) -> None:
        self.brokers = {b.name: b for b in brokers}
        self.primary: str | None = None
        self._health: dict[str, dict[str, Any]] = {}

    def set_primary(self, broker_name: str) -> None:
        """Set the primary broker."""
        if broker_name not in self.brokers:
            raise ValueError(f"Broker {broker_name} not registered")
        self.primary = broker_name

    async def health_check_all(self) -> dict[str, dict[str, Any]]:
        """Check health of all brokers."""
        for name, broker in self.brokers.items():
            try:
                self._health[name] = await broker.health_check()
            except Exception as e:
                self._health[name] = {"status": "unhealthy", "broker": name, "error": str(e)}
        return self._health

    def get_healthy_brokers(
        self, required_capability: BrokerCapabilities | None = None
    ) -> list[BrokerAdapter]:
        """Get list of healthy brokers, optionally filtered by capability."""
        healthy = []
        for name, broker in self.brokers.items():
            health = self._health.get(name, {})
            if health.get("status") == "healthy":
                if required_capability is None or required_capability in broker.capabilities:
                    healthy.append(broker)
        return healthy

    async def place_order(self, order: OrderIntent) -> OrderRecord:
        """Place an order with failover logic."""
        required_cap = self._get_required_capability(order)

        # Try primary broker first
        if self.primary and self.primary in self.brokers:
            primary_broker = self.brokers[self.primary]
            if required_cap is None or required_cap in primary_broker.capabilities:
                try:
                    return await primary_broker.place_order(order)
                except BrokerError as e:
                    if e.category not in (
                        BrokerErrorCategory.TRANSIENT,
                        BrokerErrorCategory.RATE_LIMITED,
                    ):
                        raise
                    # Fall through to failover
                except Exception as e:
                    classified = classify_error(e, self.primary)
                    if classified.category not in (
                        BrokerErrorCategory.TRANSIENT,
                        BrokerErrorCategory.RATE_LIMITED,
                    ):
                        raise

        # Try other healthy brokers with required capability
        for broker in self.get_healthy_brokers(required_cap):
            if broker.name == self.primary:
                continue
            try:
                return await broker.place_order(order)
            except BrokerError as e:
                if e.category not in (
                    BrokerErrorCategory.TRANSIENT,
                    BrokerErrorCategory.RATE_LIMITED,
                ):
                    continue
            except Exception as e:
                classified = classify_error(e, broker.name)
                if classified.category not in (
                    BrokerErrorCategory.TRANSIENT,
                    BrokerErrorCategory.RATE_LIMITED,
                ):
                    continue

        raise BrokerUnavailable(f"No available broker for order with capability {required_cap}")

    async def cancel_order(self, order_id: str) -> OrderRecord:
        """Cancel an order - tries all brokers since we don't know which one has it."""
        last_error = None
        for broker in self.brokers.values():
            try:
                return await broker.cancel_order(order_id)
            except Exception as e:
                last_error = e
                continue
        raise BrokerUnavailable(f"Failed to cancel order {order_id}: {last_error}")

    async def list_orders(self, status: Any = None) -> list[OrderRecord]:
        """List orders from all brokers."""
        all_orders: list[OrderRecord] = []
        for broker in self.brokers.values():
            try:
                orders = await broker.list_orders(status)
                all_orders.extend(orders)
            except Exception:
                continue
        return all_orders

    async def get_positions(self) -> list:
        """Get positions from all brokers (aggregated)."""
        all_positions = []
        for broker in self.brokers.values():
            try:
                positions = await broker.get_positions()
                all_positions.extend(positions)
            except Exception:
                continue
        return all_positions

    async def get_portfolio(self) -> Any:
        """Get aggregated portfolio from all brokers."""
        # This would need proper aggregation logic
        # For now, return primary broker's portfolio
        if self.primary and self.primary in self.brokers:
            return await self.brokers[self.primary].get_portfolio()
        for broker in self.brokers.values():
            try:
                return await broker.get_portfolio()
            except Exception:
                continue
        raise BrokerUnavailable("No broker available for portfolio")

    def _get_required_capability(self, order: OrderIntent) -> BrokerCapabilities | None:
        """Determine required capability from order."""
        # This is a simplified mapping - in reality would be more sophisticated
        if order.order_type in (OrderType.MARKET, OrderType.LIMIT):
            return BrokerCapabilities.MARKET_ORDERS
        return None
