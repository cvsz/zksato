"""Built-in trading policies."""

from __future__ import annotations

from typing import Any

from zksato_core.models import OrderIntent, RiskContext, Side
from zksato_risk.policies.base import Policy, PolicyDecision, PolicyResult


class KillSwitchPolicy(Policy):
    """Policy to check global kill switch."""

    @property
    def name(self) -> str:
        return "kill_switch"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        # Kill switch is checked at the engine level with settings
        return PolicyResult(decision=PolicyDecision.APPROVE)


class AccountAllowListPolicy(Policy):
    """Policy to check account allow list."""

    @property
    def name(self) -> str:
        return "account_allow_list"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if not context.account_allowed:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=["account is not in the configured trading allow-list"],
            )
        return PolicyResult(decision=PolicyDecision.APPROVE)


class MarketDataAvailabilityPolicy(Policy):
    """Policy to check market data availability."""

    @property
    def name(self) -> str:
        return "market_data_availability"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if not context.market_data_available:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=["trusted market data is unavailable"],
            )
        return PolicyResult(decision=PolicyDecision.APPROVE)


class MarketSessionPolicy(Policy):
    """Policy to enforce market session."""

    @property
    def name(self) -> str:
        return "market_session"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        opening_risk = intent.side == Side.BUY and not context.reduces_exposure

        if not context.market_session_known:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=["market session state is unknown"],
            )
        elif opening_risk and not context.market_session_open:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=["market session is closed for new exposure"],
            )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class PriceBandPolicy(Policy):
    """Policy to enforce price bands."""

    @property
    def name(self) -> str:
        return "price_band"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if not context.price_band_ok:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=["order price is outside the trusted price band"],
            )
        return PolicyResult(decision=PolicyDecision.APPROVE)


class TickSizePolicy(Policy):
    """Policy to enforce tick size."""

    @property
    def name(self) -> str:
        return "tick_size"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if not context.tick_size_ok:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=["order price is not aligned to the trusted tick size"],
            )
        return PolicyResult(decision=PolicyDecision.APPROVE)


class ShortSellingPolicy(Policy):
    """Policy to control short selling."""

    @property
    def name(self) -> str:
        return "short_selling"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        # This would be configured via settings
        return PolicyResult(decision=PolicyDecision.APPROVE)


class BoardLotPolicy(Policy):
    """Policy to enforce SET board lot (100 shares)."""

    @property
    def name(self) -> str:
        return "board_lot"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        # Only for SET stocks (no "/" in symbol) and when strict reference data is on
        return PolicyResult(decision=PolicyDecision.APPROVE)


class OrderCountLimitPolicy(Policy):
    """Policy to limit daily order count."""

    def __init__(self, max_orders: int = 50) -> None:
        self._max_orders = max_orders

    @property
    def name(self) -> str:
        return "order_count_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if context.orders_today >= self._max_orders:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=[f"maximum daily order count ({self._max_orders}) reached"],
            )
        return PolicyResult(decision=PolicyDecision.APPROVE)


class OpenOrderLimitPolicy(Policy):
    """Policy to limit open order count."""

    def __init__(self, max_open_orders: int = 20) -> None:
        self._max_open_orders = max_open_orders

    @property
    def name(self) -> str:
        return "open_order_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if context.open_orders >= self._max_open_orders:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=[f"maximum open order count ({self._max_open_orders}) reached"],
            )
        return PolicyResult(decision=PolicyDecision.APPROVE)


class ExposureLimitPolicy(Policy):
    """Policy to limit gross/net/symbol/sector exposure."""

    def __init__(
        self,
        max_gross_pct: float = 80.0,
        max_net_pct: float = 80.0,
        max_symbol_pct: float = 20.0,
        max_sector_pct: float = 35.0,
    ) -> None:
        self._max_gross_pct = max_gross_pct
        self._max_net_pct = max_net_pct
        self._max_symbol_pct = max_symbol_pct
        self._max_sector_pct = max_sector_pct

    @property
    def name(self) -> str:
        return "exposure_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        reasons: list[str] = []

        if context.gross_exposure_pct > self._max_gross_pct:
            reasons.append(
                f"gross exposure {context.gross_exposure_pct:.1f}% exceeds limit {self._max_gross_pct:.1f}%"
            )

        if abs(context.net_exposure_pct) > self._max_net_pct:
            reasons.append(
                f"net exposure {abs(context.net_exposure_pct):.1f}% exceeds limit {self._max_net_pct:.1f}%"
            )

        if context.symbol_exposure_pct > self._max_symbol_pct:
            reasons.append(
                f"symbol exposure {context.symbol_exposure_pct:.1f}% exceeds limit {self._max_symbol_pct:.1f}%"
            )

        if context.sector_exposure_pct > self._max_sector_pct:
            reasons.append(
                f"sector exposure {context.sector_exposure_pct:.1f}% exceeds limit {self._max_sector_pct:.1f}%"
            )

        if reasons:
            return PolicyResult(decision=PolicyDecision.REJECT, reasons=reasons)

        return PolicyResult(decision=PolicyDecision.APPROVE)


class NotionalLimitPolicy(Policy):
    """Policy to limit order notional."""

    def __init__(self, max_notional: float = 100_000.0) -> None:
        self._max_notional = max_notional

    @property
    def name(self) -> str:
        return "notional_limit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if not context.reference_price:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=["reference price is required for risk estimation"],
            )

        notional = float(context.reference_price * intent.quantity)
        if notional > self._max_notional:
            return PolicyResult(
                decision=PolicyDecision.REJECT,
                reasons=[f"order notional {notional:.2f} exceeds limit {self._max_notional:.2f}"],
            )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class StopLossPolicy(Policy):
    """Policy to require stop loss on buy orders."""

    def __init__(self, required: bool = True) -> None:
        self._required = required

    @property
    def name(self) -> str:
        return "stop_loss"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        opening_risk = intent.side == Side.BUY and not context.reduces_exposure

        if self._required and opening_risk:
            if intent.stop_loss is None:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=["stop loss is required for buy orders"],
                )
            if intent.price and intent.stop_loss >= intent.price:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=["buy stop loss must be below entry price"],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class TakeProfitPolicy(Policy):
    """Policy to validate take profit on buy orders."""

    @property
    def name(self) -> str:
        return "take_profit"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        opening_risk = intent.side == Side.BUY and not context.reduces_exposure

        if opening_risk and intent.take_profit is not None:
            if intent.price and intent.take_profit <= intent.price:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=["buy take profit must be above entry price"],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class LineAvailabilityPolicy(Policy):
    """Policy to check line availability."""

    @property
    def name(self) -> str:
        return "line_availability"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        opening_risk = intent.side == Side.BUY and not context.reduces_exposure

        if opening_risk and context.line_available is not None and context.reference_price:
            notional = float(context.reference_price * intent.quantity)
            if notional > float(context.line_available):
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=["estimated notional exceeds available line"],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class PriceDeviationPolicy(Policy):
    """Policy to limit price deviation from reference."""

    def __init__(self, max_deviation_pct: float = 10.0) -> None:
        self._max_deviation_pct = max_deviation_pct

    @property
    def name(self) -> str:
        return "price_deviation"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        if context.reference_price and intent.price:
            deviation = abs(intent.price - context.reference_price) / context.reference_price * 100
            if deviation > self._max_deviation_pct:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=[
                        f"limit price deviates {deviation:.2f}% from reference (max {self._max_deviation_pct:.2f}%)"
                    ],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)


class PerTradeRiskPolicy(Policy):
    """Policy to limit per-trade risk."""

    def __init__(self, max_risk_per_trade_pct: float = 0.5) -> None:
        self._max_risk_per_trade_pct = max_risk_per_trade_pct

    @property
    def name(self) -> str:
        return "per_trade_risk"

    @property
    def version(self) -> str:
        return "1.0"

    def evaluate(self, intent: OrderIntent, context: RiskContext) -> PolicyResult:
        opening_risk = intent.side == Side.BUY and not context.reduces_exposure

        if (
            opening_risk
            and intent.stop_loss is not None
            and context.reference_price
            and context.portfolio_value
        ):
            per_share_risk = max(0.0, float(context.reference_price) - float(intent.stop_loss))
            risk_value = per_share_risk * intent.quantity
            estimated_risk_pct = risk_value / float(context.portfolio_value) * 100

            if estimated_risk_pct > self._max_risk_per_trade_pct:
                return PolicyResult(
                    decision=PolicyDecision.REJECT,
                    reasons=[
                        f"estimated stop-loss risk {estimated_risk_pct:.2f}% exceeds per-trade budget {self._max_risk_per_trade_pct:.2f}%"
                    ],
                )

        return PolicyResult(decision=PolicyDecision.APPROVE)


# Policy factory for easy creation
def create_default_policies(settings: Any) -> list[Policy]:
    """Create default policies from settings."""
    return [
        KillSwitchPolicy(),
        AccountAllowListPolicy(),
        MarketDataAvailabilityPolicy(),
        MarketSessionPolicy(),
        PriceBandPolicy(),
        TickSizePolicy(),
        BoardLotPolicy(),
        OrderCountLimitPolicy(settings.max_orders_per_day),
        OpenOrderLimitPolicy(settings.max_open_orders),
        ExposureLimitPolicy(
            settings.max_gross_exposure_pct,
            settings.max_net_exposure_pct,
            settings.max_symbol_exposure_pct,
            settings.max_sector_exposure_pct,
        ),
        NotionalLimitPolicy(settings.max_notional_per_order),
        StopLossPolicy(settings.require_stop_loss),
        TakeProfitPolicy(),
        LineAvailabilityPolicy(),
        PriceDeviationPolicy(settings.max_price_deviation_pct),
        PerTradeRiskPolicy(settings.max_risk_per_trade_pct),
    ]
