"""Session reconciliation for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from zksato_core.models import OrderRecord, PortfolioSnapshot

from zksato_portfolio.portfolio import PortfolioManager
from zksato_portfolio.reconcile import ReconciliationEngine


@dataclass
class SessionReconciliation:
    """Handles session-based reconciliation on startup."""

    portfolio_manager: PortfolioManager
    reconciliation_engine: ReconciliationEngine

    async def reconcile_on_startup(
        self,
        broker_portfolio: PortfolioSnapshot,
        broker_orders: list[OrderRecord],
        local_orders: list[OrderRecord],
    ) -> dict[str, Any]:
        """Run full reconciliation on session startup."""

        # Reconcile portfolio
        portfolio_result = await self.reconciliation_engine.reconcile(broker_portfolio)

        # Reconcile orders
        orders_result = await self.reconciliation_engine.reconcile_orders(
            local_orders, broker_orders
        )

        # Determine actions needed
        actions = []

        if not portfolio_result.matched:
            actions.append(
                {
                    "type": "portfolio_sync",
                    "details": portfolio_result.discrepancies,
                    "priority": "high",
                }
            )

        if not orders_result.matched:
            actions.append(
                {
                    "type": "order_sync",
                    "details": orders_result.discrepancies,
                    "priority": "high",
                }
            )

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "portfolio_matched": portfolio_result.matched,
            "orders_matched": orders_result.matched,
            "actions": actions,
            "portfolio_discrepancies": portfolio_result.discrepancies,
            "order_discrepancies": orders_result.discrepancies,
        }

    async def reconcile_positions(
        self,
        broker_positions: list[Any],
    ) -> dict[str, Any]:
        """Reconcile positions specifically."""
        local = await self.portfolio_manager.snapshot()

        discrepancies = []
        local_symbols = {p.symbol: p for p in local.positions}
        broker_symbols = {p.symbol: p for p in broker_positions}

        for symbol in set(local_symbols) | set(broker_symbols):
            local_pos = local_symbols.get(symbol)
            broker_pos = broker_symbols.get(symbol)

            if local_pos and not broker_pos:
                discrepancies.append(
                    {"type": "orphan_local", "symbol": symbol, "quantity": local_pos.quantity}
                )
            elif broker_pos and not local_pos:
                discrepancies.append(
                    {"type": "orphan_broker", "symbol": symbol, "quantity": broker_pos.quantity}
                )
            elif local_pos and broker_pos and local_pos.quantity != broker_pos.quantity:
                discrepancies.append(
                    {
                        "type": "quantity_mismatch",
                        "symbol": symbol,
                        "local": local_pos.quantity,
                        "broker": broker_pos.quantity,
                    }
                )

        return {
            "matched": len(discrepancies) == 0,
            "discrepancies": discrepancies,
        }
