from __future__ import annotations

from zksato.config import Settings
from zksato.domain import OrderIntent, RiskContext, RiskDecision, Side


class RiskEngine:
    """Deterministic pre-trade checks that automation and AI cannot bypass."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> RiskDecision:
        reasons: list[str] = []
        price = intent.price or context.reference_price or 0.0
        estimated_notional = price * intent.quantity if price > 0 else 0.0
        estimated_risk_pct: float | None = None

        if self.settings.kill_switch:
            reasons.append("global kill switch is active")

        if context.daily_pnl_pct <= -abs(self.settings.max_daily_loss_pct):
            reasons.append("maximum daily loss threshold reached")

        if context.drawdown_pct >= self.settings.max_drawdown_pct:
            reasons.append("maximum drawdown threshold reached")

        if intent.side == Side.BUY and context.current_positions >= self.settings.max_positions:
            reasons.append("maximum number of positions reached")

        if context.position_pct_after_trade > self.settings.max_position_pct:
            reasons.append("position size exceeds maximum portfolio percentage")

        if context.orders_today >= self.settings.max_orders_per_day:
            reasons.append("maximum daily order count reached")

        if estimated_notional > self.settings.max_notional_per_order:
            reasons.append("order notional exceeds configured maximum")

        if (
            self.settings.require_stop_loss
            and intent.side == Side.BUY
            and intent.stop_loss is None
        ):
            reasons.append("stop loss is required for buy orders")

        if (
            intent.side == Side.BUY
            and intent.price is not None
            and intent.stop_loss is not None
            and intent.stop_loss >= intent.price
        ):
            reasons.append("buy stop loss must be below entry price")

        if (
            intent.side == Side.BUY
            and intent.take_profit is not None
            and intent.price is not None
            and intent.take_profit <= intent.price
        ):
            reasons.append("buy take profit must be above entry price")

        if context.line_available is not None and intent.side == Side.BUY:
            if estimated_notional > context.line_available:
                reasons.append("estimated notional exceeds available line")

        if context.reference_price and intent.price:
            deviation = abs(intent.price - context.reference_price) / context.reference_price * 100
            if deviation > self.settings.max_price_deviation_pct:
                reasons.append("limit price deviates too far from reference price")

        if intent.side == Side.BUY and intent.stop_loss is not None and price > 0:
            per_share_risk = max(0.0, price - intent.stop_loss)
            risk_value = per_share_risk * intent.quantity
            if context.portfolio_value and context.portfolio_value > 0:
                estimated_risk_pct = risk_value / context.portfolio_value * 100
                if estimated_risk_pct > self.settings.max_risk_per_trade_pct:
                    reasons.append("estimated stop-loss risk exceeds per-trade risk budget")

        return RiskDecision(
            approved=not reasons,
            reasons=reasons,
            estimated_notional=estimated_notional,
            estimated_risk_pct=estimated_risk_pct,
        )
