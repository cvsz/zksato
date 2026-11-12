"""Test data generators for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from zksato_core.types import OrderType, OrderStatus, Side
from zksato_core.models import OrderRecord, FillRecord


@dataclass
class OrderGenerator:
    """Generates test orders."""
    
    @staticmethod
    def generate_order(
        symbol: str = "TEST",
        side: Side = Side.BUY,
        quantity: float = 100,
        order_type: OrderType = OrderType.LIMIT,
        price: float = 100.0,
        status: OrderStatus = OrderStatus.ACCEPTED,
        **kwargs,
    ) -> OrderRecord:
        """Generate a single order."""
        return OrderRecord(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price if order_type == OrderType.LIMIT else None,
            status=status,
            source="test",
            **kwargs,
        )
    
    @staticmethod
    def generate_orders(
        count: int = 10,
        symbol: str = "TEST",
        **kwargs,
    ) -> list[OrderRecord]:
        """Generate multiple orders."""
        return [OrderGenerator.generate_order(symbol=symbol, **kwargs) for _ in range(count)]


@dataclass
class FillGenerator:
    """Generates test fills."""
    
    @staticmethod
    def generate_fill(
        order_id: str,
        symbol: str = "TEST",
        side: Side = Side.BUY,
        quantity: float = 100,
        price: float = 100.0,
        **kwargs,
    ) -> FillRecord:
        """Generate a single fill."""
        return FillRecord(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            source="test",
            **kwargs,
        )
    
    @staticmethod
    def generate_fills(
        count: int = 10,
        order_id: str = "test_order",
        **kwargs,
    ) -> list[FillRecord]:
        """Generate multiple fills."""
        return [FillGenerator.generate_fill(order_id=order_id, **kwargs) for _ in range(count)]


def generate_orders(count: int = 10, **kwargs) -> list[OrderRecord]:
    """Generate test orders."""
    return OrderGenerator.generate_orders(count, **kwargs)


def generate_fills(count: int = 10, **kwargs) -> list[FillRecord]:
    """Generate test fills."""
    return FillGenerator.generate_fills(count, **kwargs)