"""Notional and loss limit checks."""

from __future__ import annotations

from zksato_core.models import OrderIntent, RiskContext, Side
from zksato_risk.checks.base import BaseRiskCheck


class NotionalLimitCheck(BaseRiskCheck):
    """Check order notional limit."""

    def __init__(self, max_notional: float = 100_000.0) -> None:
        self.max_notional = max_notional
        self.name = "notional_limit"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if not context.reference_price:
            return ["reference price is required for risk estimation"]

        estimated_notional = float(context.reference_price * intent.quantity)
        if estimated_notional > self.max_notional:
            return [
                f"order notional {estimated_notional:.2f} exceeds limit {self.max_notional:.2f}"
            ]
        return []


class DailyLossLimitCheck(BaseRiskCheck):
    """Check daily loss limit."""

    def __init__(self, max_daily_loss_pct: float = 2.0) -> None:
        self.max_daily_loss_pct = max_daily_loss_pct
        self.name = "daily_loss_limit"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if (
            intent.side == Side.BUY
            and not context.reduces_exposure
            and context.daily_pnl_pct <= -abs(self.max_daily_loss_pct)
        ):
            return [f"maximum daily loss threshold ({self.max_daily_loss_pct}%) reached"]
        return []


class DrawdownLimitCheck(BaseRiskCheck):
    """Check drawdown limit."""

    def __init__(self, max_drawdown_pct: float = 5.0) -> None:
        self.max_drawdown_pct = max_drawdown_pct
        self.name = "drawdown_limit"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if (
            intent.side == Side.BUY
            and not context.reduces_exposure
            and context.drawdown_pct >= self.max_drawdown_pct
        ):
            return [f"maximum drawdown threshold ({self.max_drawdown_pct}%) reached"]
        return []


class GrossExposureCheck(BaseRiskCheck):
    """Check gross exposure limit."""

    def __init__(self, max_gross_exposure_pct: float = 80.0) -> None:
        self.max_gross_exposure_pct = max_gross_exposure_pct
        self.name = "gross_exposure"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if (
            intent.side == Side.BUY
            and not context.reduces_exposure
            and context.gross_exposure_pct > self.max_gross_exposure_pct
        ):
            return [
                f"gross exposure {context.gross_exposure_pct:.1f}% exceeds limit {self.max_gross_exposure_pct:.1f}%"
            ]
        return []


class NetExposureCheck(BaseRiskCheck):
    """Check net exposure limit."""

    def __init__(self, max_net_exposure_pct: float = 80.0) -> None:
        self.max_net_exposure_pct = max_net_exposure_pct
        self.name = "net_exposure"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if (
            intent.side == Side.BUY
            and not context.reduces_exposure
            and abs(context.net_exposure_pct) > self.max_net_exposure_pct
        ):
            return [
                f"net exposure {abs(context.net_exposure_pct):.1f}% exceeds limit {self.max_net_exposure_pct:.1f}%"
            ]
        return []


class LineAvailabilityCheck(BaseRiskCheck):
    """Check line availability."""

    def __init__(self) -> None:
        self.name = "line_availability"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if (
            intent.side == Side.BUY
            and not context.reduces_exposure
            and context.line_available is not None
            and context.reference_price
        ):
            estimated_notional = float(context.reference_price * intent.quantity)
            if estimated_notional > float(context.line_available):
                return ["estimated notional exceeds available line"]
        return []


class PerTradeRiskCheck(BaseRiskCheck):
    """Check per-trade risk limit."""

    def __init__(self, max_risk_per_trade_pct: float = 0.5) -> None:
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.name = "per_trade_risk"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if (
            intent.side == Side.BUY
            and not context.reduces_exposure
            and intent.stop_loss is not None
            and context.reference_price
            and context.portfolio_value
        ):
            per_share_risk = max(0.0, float(context.reference_price) - float(intent.stop_loss))
            risk_value = per_share_risk * intent.quantity
            estimated_risk_pct = risk_value / float(context.portfolio_value) * 100

            if estimated_risk_pct > self.max_risk_per_trade_pct:
                return [
                    f"estimated stop-loss risk {estimated_risk_pct:.2f}% exceeds per-trade budget {self.max_risk_per_trade_pct:.2f}%"
                ]
        return []


class StopLossCheck(BaseRiskCheck):
    """Check stop loss requirement."""

    def __init__(self, required: bool = True) -> None:
        self.required = required
        self.name = "stop_loss"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if self.required and intent.side == Side.BUY and not context.reduces_exposure:
            if intent.stop_loss is None:
                return ["stop loss is required for buy orders"]
            if context.reference_price and intent.stop_loss >= context.reference_price:
                return ["buy stop loss must be below entry price"]
        return []


class TakeProfitCheck(BaseRiskCheck):
    """Check take profit validity."""

    def __init__(self) -> None:
        self.name = "take_profit"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if (
            intent.side == Side.BUY
            and not context.reduces_exposure
            and intent.take_profit is not None
            and context.reference_price
            and intent.take_profit <= context.reference_price
        ):
            return ["buy take profit must be above entry price"]
        return []


class PriceDeviationCheck(BaseRiskCheck):
    """Check price deviation from reference."""

    def __init__(self, max_deviation_pct: float = 10.0) -> None:
        self.max_deviation_pct = max_deviation_pct
        self.name = "price_deviation"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if context.reference_price and intent.price:
            deviation = (
                abs(float(intent.price) - float(context.reference_price))
                / float(context.reference_price)
                * 100
            )
            if deviation > self.max_deviation_pct:
                return [
                    f"limit price deviates {deviation:.2f}% from reference (max {self.max_deviation_pct:.2f}%)"
                ]
        return []
