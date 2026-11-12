"""Reconciliation engine for zksato."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from zksato_core.models import PortfolioSnapshot, Position, OrderRecord, ReconciliationReport
from zksato_portfolio.portfolio import PortfolioManager


@dataclass
class ReconciliationResult:
    """Result of a reconciliation."""
    matched: bool
    local_portfolio: PortfolioSnapshot
    broker_portfolio: PortfolioSnapshot
    discrepancies: list[dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ReconciliationEngine:
    """Reconciles local portfolio state with broker state."""
    
    def __init__(self, portfolio_manager: PortfolioManager) -> None:
        self.portfolio = portfolio_manager
        self.tolerance_pct = 0.01  # 1% tolerance
    
    async def reconcile(self, broker_portfolio: PortfolioSnapshot) -> ReconciliationResult:
        """Reconcile local portfolio with broker."""
        local = await self.portfolio.snapshot()
        
        discrepancies = []
        
        # Compare cash
        cash_diff = abs(local.cash - broker_portfolio.cash)
        cash_tolerance = max(local.cash, broker_portfolio.cash) * self.tolerance_pct
        if cash_diff > cash_tolerance:
            discrepancies.append({
                "type": "cash_mismatch",
                "local": local.cash,
                "broker": broker_portfolio.cash,
                "diff": cash_diff,
            })
        
        # Compare positions
        local_symbols = set(local.positions.keys())
        broker_symbols = set(p.symbol for p in broker_portfolio.positions)
        all_symbols = local_symbols | broker_symbols
        
        for symbol in all_symbols:
            local_pos = next((p for p in local.positions if p.symbol == symbol), None)
            broker_pos = next((p for p in broker_portfolio.positions if p.symbol == symbol), None)
            
            if local_pos and not broker_pos:
                discrepancies.append({
                    "type": "missing_position_broker",
                    "symbol": symbol,
                    "local_quantity": local_pos.quantity,
                })
            elif broker_pos and not local_pos:
                discrepancies.append({
                    "type": "missing_position_local",
                    "symbol": symbol,
                    "broker_quantity": broker_pos.quantity,
                })
            elif local_pos and broker_pos:
                qty_diff = abs(local_pos.quantity - broker_pos.quantity)
                if qty_diff > 0:
                    discrepancies.append({
                        "type": "quantity_mismatch",
                        "symbol": symbol,
                        "local_quantity": local_pos.quantity,
                        "broker_quantity": broker_pos.quantity,
                        "diff": qty_diff,
                    })
                
                price_diff = abs(local_pos.market_price - broker_pos.market_price)
                price_tolerance = max(local_pos.market_price, broker_pos.market_price) * self.tolerance_pct
                if price_diff > price_tolerance:
                    discrepancies.append({
                        "type": "price_mismatch",
                        "symbol": symbol,
                        "local_price": local_pos.market_price,
                        "broker_price": broker_pos.market_price,
                        "diff": price_diff,
                    })
        
        matched = len(discrepancies) == 0
        
        return ReconciliationResult(
            matched=matched,
            local_portfolio=local,
            broker_portfolio=broker_portfolio,
            discrepancies=discrepancies,
        )
    
    async def reconcile_orders(
        self,
        local_orders: list[OrderRecord],
        broker_orders: list[OrderRecord],
    ) -> ReconciliationResult:
        """Reconcile order lists."""
        discrepancies = []
        
        local_ids = {o.broker_order_id for o in local_orders if o.broker_order_id}
        broker_ids = {o.broker_order_id for o in broker_orders if o.broker_order_id}
        
        missing_in_local = broker_ids - local_ids
        missing_in_broker = local_ids - broker_ids
        
        for oid in missing_in_local:
            discrepancies.append({"type": "order_missing_local", "broker_order_id": oid})
        
        for oid in missing_in_broker:
            discrepancies.append({"type": "order_missing_broker", "broker_order_id": oid})
        
        # Compare matching orders
        for local_order in local_orders:
            if not local_order.broker_order_id:
                continue
            broker_order = next((o for o in broker_orders if o.broker_order_id == local_order.broker_order_id), None)
            if broker_order:
                if local_order.status != broker_order.status:
                    discrepancies.append({
                        "type": "status_mismatch",
                        "broker_order_id": local_order.broker_order_id,
                        "local_status": local_order.status.value,
                        "broker_status": broker_order.status.value,
                    })
                if local_order.filled_quantity != broker_order.filled_quantity:
                    discrepancies.append({
                        "type": "filled_qty_mismatch",
                        "broker_order_id": local_order.broker_order_id,
                        "local_filled": local_order.filled_quantity,
                        "broker_filled": broker_order.filled_quantity,
                    })
        
        return ReconciliationResult(
            matched=len(discrepancies) == 0,
            local_portfolio=await self.portfolio.snapshot(),
            broker_portfolio=PortfolioSnapshot(
                cash=0, market_value=0, equity=0,
                realized_pnl=0, unrealized_pnl=0, daily_pnl=0, positions=[]
            ),
            discrepancies=discrepancies,
        )
    
    def generate_report(self, result: ReconciliationResult) -> ReconciliationReport:
        """Generate a reconciliation report."""
        return ReconciliationReport(
            timestamp=result.timestamp,
            matched=result.matched,
            discrepancies=result.discrepancies,
            local_equity=result.local_portfolio.equity,
            broker_equity=result.broker_portfolio.equity,
        )