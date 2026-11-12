"""Trading service for zksato automation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zksato_core.models import Signal, OrderIntent, OrderRecord
from zksato_core.types import SignalAction, Side
from zksato_risk.engine import RiskEngine


@dataclass
class TradingService:
    """Core trading service that coordinates strategy, risk, and execution."""
    
    risk_engine: RiskEngine
    
    async def process_signal(self, signal: Signal) -> OrderRecord | None:
        """Process a trading signal through risk and execution."""
        if signal.action == SignalAction.HOLD:
            return None
        
        # Create order intent
        intent = OrderIntent(
            symbol=signal.symbol,
            side=Side.BUY if signal.action == SignalAction.BUY else Side.SELL,
            quantity=100,  # Would come from position sizing
            order_type="LIMIT",
            price=signal.price,
            source=f"strategy:{signal.strategy}",
        )
        
        # Risk check
        from zksato_core.models import RiskContext
        risk_context = RiskContext(
            order=intent,
            account_id="default",
            portfolio_snapshot=None,
        )
        
        risk_result = await self.risk_engine.evaluate(risk_context)
        
        if not risk_result.allowed:
            # Log rejection
            return OrderRecord(
                symbol=signal.symbol,
                side=intent.side,
                quantity=intent.quantity,
                order_type=intent.order_type,
                price=intent.price,
                status="REJECTED",
                message=risk_result.reason,
                source=intent.source,
            )
        
        # Execute order (would use broker adapter)
        # For now, return a simulated fill
        return OrderRecord(
            symbol=signal.symbol,
            side=intent.side,
            quantity=intent.quantity,
            order_type=intent.order_type,
            price=intent.price,
            status="FILLED",
            source=intent.source,
        )
    
    async def reconcile(self) -> dict[str, Any]:
        """Run reconciliation."""
        return {"status": "completed", "details": "reconciliation completed"}