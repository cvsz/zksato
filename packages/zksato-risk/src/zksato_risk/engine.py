"""RiskEngine, RiskContext, RiskResult."""

from __future__ import annotations

from dataclasses import dataclass

from zksato_core.config import BaseConfig
from zksato_core.models import OrderIntent, RiskContext, RiskDecision, Side
from zksato_core.money import thb


@dataclass(frozen=True, slots=True)
class RiskEngine:
    """Deterministic pre-trade checks that automation and AI cannot bypass."""

    settings: BaseConfig

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> RiskDecision:
        reasons: list[str] = []
        price = intent.price or context.reference_price
        estimated_notional = price * intent.quantity if price else thb(0)
        estimated_risk_pct: float | None = None
        opening_risk = intent.side == Side.BUY and not context.reduces_exposure
        is_prediction = intent.side in {Side.UP, Side.DOWN}

        if self.settings.kill_switch:
            reasons.append("global kill switch is active")
        if not context.account_allowed:
            reasons.append("account is not in the configured trading allow-list")
        if not context.market_data_available:
            reasons.append("trusted market data is unavailable")
        if not context.market_session_known:
            reasons.append("market session state is unknown")
        elif opening_risk and not context.market_session_open:
            reasons.append("market session is closed for new exposure")
        if not context.price_band_ok:
            reasons.append("order price is outside the trusted price band")
        if not context.tick_size_ok:
            reasons.append("order price is not aligned to the trusted tick size")
        if not is_prediction:
            if (
                intent.side == Side.SELL
                and not context.reduces_exposure
                and not self.settings.allow_equity_short_selling
            ):
                reasons.append("equity short selling is disabled")
            if intent.side == Side.SELL and not self.settings.allow_equity_short_selling:
                if not context.reduces_exposure:
                    if (
                        context.available_quantity is None
                        or intent.quantity > context.available_quantity
                    ):
                        reasons.append("sell quantity exceeds available position")
                elif (
                    context.available_quantity is not None
                    and intent.quantity > context.available_quantity
                ):
                    reasons.append("sell quantity exceeds available position")
            if (
                intent.side in {Side.BUY, Side.SELL}
                and self.settings.strict_reference_data
                and "/" not in intent.symbol
            ):
                if float(intent.quantity) != int(intent.quantity):
                    reasons.append("SET quantity must be integer")
                elif int(intent.quantity) % 100 != 0:
                    reasons.append("SET quantity must be multiple of 100 (board lot)")
            if opening_risk and context.daily_pnl_pct <= -abs(self.settings.max_daily_loss_pct):
                reasons.append("maximum daily loss threshold reached")
            if opening_risk and context.drawdown_pct >= self.settings.max_drawdown_pct:
                reasons.append("maximum drawdown threshold reached")
            if (
                opening_risk
                and context.opens_new_position
                and context.current_positions >= self.settings.max_positions
            ):
                reasons.append("maximum number of positions reached")
            if opening_risk and context.position_pct_after_trade > self.settings.max_position_pct:
                reasons.append("position size exceeds maximum portfolio percentage")
            if context.orders_today >= self.settings.max_orders_per_day:
                reasons.append("maximum daily order count reached")
            if context.open_orders >= self.settings.max_open_orders:
                reasons.append("maximum open order count reached")
            if opening_risk and context.gross_exposure_pct > self.settings.max_gross_exposure_pct:
                reasons.append("gross exposure exceeds configured maximum")
            if opening_risk and abs(context.net_exposure_pct) > self.settings.max_net_exposure_pct:
                reasons.append("net exposure exceeds configured maximum")
            if opening_risk and context.symbol_exposure_pct > self.settings.max_symbol_exposure_pct:
                reasons.append("symbol exposure exceeds configured maximum")
            if opening_risk and context.sector_exposure_pct > self.settings.max_sector_exposure_pct:
                reasons.append("sector exposure exceeds configured maximum")
            if (
                context.quote_age_seconds is not None
                and context.quote_age_seconds > self.settings.market_data_stale_seconds
            ):
                reasons.append("market quote is stale")
            if context.spread_pct is not None and context.spread_pct > self.settings.max_spread_pct:
                reasons.append("bid/offer spread exceeds configured maximum")
            if estimated_notional <= thb(0):
                reasons.append("reference price is required for risk estimation")
            elif estimated_notional > thb(self.settings.max_notional_per_order):
                reasons.append("order notional exceeds configured maximum")
            if self.settings.require_stop_loss and opening_risk and intent.stop_loss is None:
                reasons.append("stop loss is required for buy orders")
            if (
                opening_risk
                and intent.stop_loss is not None
                and price
                and intent.stop_loss.to_float() >= price.to_float()
            ):
                reasons.append("buy stop loss must be below entry price")
            if (
                opening_risk
                and intent.take_profit is not None
                and price
                and intent.take_profit.to_float() <= price.to_float()
            ):
                reasons.append("buy take profit must be above entry price")
            if (
                context.line_available is not None
                and opening_risk
                and estimated_notional > context.line_available
            ):
                reasons.append("estimated notional exceeds available line")
            if context.reference_price and intent.price:
                diff = intent.price.to_float() - context.reference_price.to_float()
                deviation = abs(diff) / context.reference_price.to_float() * 100
                if deviation > self.settings.max_price_deviation_pct:
                    reasons.append("limit price deviates too far from reference price")
            if opening_risk and intent.stop_loss is not None and price:
                per_share_risk = max(0.0, price.to_float() - intent.stop_loss.to_float())
                risk_value = per_share_risk * intent.quantity
                if context.portfolio_value and context.portfolio_value.to_float() > 0:
                    estimated_risk_pct = risk_value / context.portfolio_value.to_float() * 100
                    if estimated_risk_pct > self.settings.max_risk_per_trade_pct:
                        reasons.append("estimated stop-loss risk exceeds per-trade risk budget")
        else:
            if (
                context.quote_age_seconds is not None
                and context.quote_age_seconds > self.settings.market_data_stale_seconds
            ):
                reasons.append("prediction feed is stale")
            if estimated_notional <= thb(0):
                reasons.append("reference price is required for risk estimation")
            elif estimated_notional > thb(self.settings.max_notional_per_order):
                reasons.append("order notional exceeds configured maximum")
            if estimated_notional > thb(self.settings.prediction_max_order_usd):
                reasons.append("prediction order exceeds configured per-order USD limit")
            if (
                context.prediction_directional_residual is not None
                and context.prediction_directional_residual > self.settings.max_directional_residual
            ):
                reasons.append("directional residual exceeds configured maximum")
            if (
                context.prediction_complete_set_cost is not None
                and context.prediction_complete_set_cost > self.settings.max_complete_set_cost
            ):
                reasons.append("complete-set cost exceeds configured maximum")
            if (
                context.prediction_edge is not None
                and context.prediction_edge < self.settings.min_prediction_edge
            ):
                reasons.append("model edge is below minimum threshold")

        return RiskDecision(
            approved=not reasons,
            reasons=reasons,
            estimated_notional=estimated_notional,
            estimated_risk_pct=estimated_risk_pct,
        )
