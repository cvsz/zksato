from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from zksato.broker.base import Broker
from zksato.domain import Side
from zksato.store import StateStore


class PositionDiscrepancy(BaseModel):
    symbol: str
    expected_quantity: int
    broker_quantity: int
    difference: int


class SessionReconciliationReport(BaseModel):
    matched: bool
    expected_positions: dict[str, int]
    broker_positions: dict[str, int]
    discrepancies: list[PositionDiscrepancy] = Field(default_factory=list)
    unresolved_orders: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SessionReconciliationService:
    """Independent end-of-session comparison derived from durable fills."""

    def __init__(self, broker: Broker, store: StateStore) -> None:
        self.broker = broker
        self.store = store

    async def run(self) -> SessionReconciliationReport:
        expected: defaultdict[str, int] = defaultdict(int)
        for fill in reversed(self.store.list_fills(limit=100_000)):
            direction = 1 if fill.side == Side.BUY else -1
            expected[fill.symbol] += direction * fill.quantity
        expected_clean = {symbol: quantity for symbol, quantity in expected.items() if quantity != 0}

        portfolio = await self.broker.portfolio()
        broker_positions = {
            position.symbol: int(position.quantity)
            for position in portfolio.positions
            if int(position.quantity) != 0
        }
        symbols = sorted(set(expected_clean) | set(broker_positions))
        discrepancies = [
            PositionDiscrepancy(
                symbol=symbol,
                expected_quantity=expected_clean.get(symbol, 0),
                broker_quantity=broker_positions.get(symbol, 0),
                difference=broker_positions.get(symbol, 0) - expected_clean.get(symbol, 0),
            )
            for symbol in symbols
            if expected_clean.get(symbol, 0) != broker_positions.get(symbol, 0)
        ]
        unresolved = [
            str(order.id)
            for order in self.store.list_orders()
            if order.status.value == "needs_reconciliation"
        ]
        report = SessionReconciliationReport(
            matched=not discrepancies and not unresolved,
            expected_positions=expected_clean,
            broker_positions=broker_positions,
            discrepancies=discrepancies,
            unresolved_orders=unresolved,
        )
        self.store.add_audit(
            "session_reconciliation.completed",
            "session fill/position reconciliation completed",
            {
                "matched": report.matched,
                "discrepancies": len(discrepancies),
                "unresolved_orders": len(unresolved),
            },
        )
        return report
