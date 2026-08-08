from __future__ import annotations

from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, RiskDecision, Side


class RiskEngine:
    """Deterministic pre-trade checks.

    This layer must remain independent from any LLM/agent decision. AI components may
    propose a signal, but they cannot bypass these rules.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> RiskDecision:
        reasons: list[str] = []

        if context.daily_pnl_pct <= -abs(self.settings.max_daily_loss_pct):
            reasons.append("maximum daily loss threshold reached")

        if context.drawdown_pct >= self.settings.max_drawdown_pct:
            reasons.append("maximum drawdown threshold reached")

        if (
            intent.side == Side.BUY
            and context.current_positions >= self.settings.max_positions
        ):
            reasons.append("maximum number of positions reached")

        if context.position_pct_after_trade > self.settings.max_position_pct:
            reasons.append("position size exceeds maximum portfolio percentage")

        if (
            self.settings.require_stop_loss
            and intent.side == Side.BUY
            and intent.stop_loss is None
        ):
            reasons.append("stop loss is required for buy orders")

        if intent.side == Side.BUY and intent.price is not None and intent.stop_loss is not None:
            if intent.stop_loss >= intent.price:
                reasons.append("buy stop loss must be below entry price")

        if context.line_available is not None and intent.price is not None:
            estimated_notional = intent.price * intent.quantity
            if intent.side == Side.BUY and estimated_notional > context.line_available:
                reasons.append("estimated notional exceeds available line")

        return RiskDecision(approved=not reasons, reasons=reasons)
