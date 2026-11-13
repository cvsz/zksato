"""Market data and session checks."""

from __future__ import annotations

from zksato_core.models import OrderIntent, RiskContext, Side
from zksato_risk.checks.base import BaseRiskCheck


class MarketDataAvailabilityCheck(BaseRiskCheck):
    """Check market data availability."""

    def __init__(self) -> None:
        self.name = "market_data_availability"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if not context.market_data_available:
            return ["trusted market data is unavailable"]
        return []


class MarketSessionCheck(BaseRiskCheck):
    """Check market session state."""

    def __init__(self) -> None:
        self.name = "market_session"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        reasons: list[str] = []
        opening_risk = intent.side == Side.BUY and not context.reduces_exposure

        if not context.market_session_known:
            reasons.append("market session state is unknown")
        elif opening_risk and not context.market_session_open:
            reasons.append("market session is closed for new exposure")

        return reasons


class QuoteStalenessCheck(BaseRiskCheck):
    """Check quote freshness."""

    def __init__(self, max_age_seconds: float = 10.0) -> None:
        self.max_age_seconds = max_age_seconds
        self.name = "quote_staleness"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if (
            context.quote_age_seconds is not None
            and context.quote_age_seconds > self.max_age_seconds
        ):
            return [
                f"market quote is stale ({context.quote_age_seconds:.1f}s > {self.max_age_seconds:.1f}s)"
            ]
        return []


class SpreadCheck(BaseRiskCheck):
    """Check bid/ask spread."""

    def __init__(self, max_spread_pct: float = 3.0) -> None:
        self.max_spread_pct = max_spread_pct
        self.name = "spread"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if context.spread_pct is not None and context.spread_pct > self.max_spread_pct:
            return [
                f"bid/offer spread {context.spread_pct:.2f}% exceeds limit {self.max_spread_pct:.2f}%"
            ]
        return []


class PriceBandCheck(BaseRiskCheck):
    """Check price band."""

    def __init__(self) -> None:
        self.name = "price_band"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if not context.price_band_ok:
            return ["order price is outside the trusted price band"]
        return []


class TickSizeCheck(BaseRiskCheck):
    """Check tick size alignment."""

    def __init__(self) -> None:
        self.name = "tick_size"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if not context.tick_size_ok:
            return ["order price is not aligned to the trusted tick size"]
        return []


class OrderCountCheck(BaseRiskCheck):
    """Check daily order count."""

    def __init__(self, max_orders_per_day: int = 50) -> None:
        self.max_orders_per_day = max_orders_per_day
        self.name = "order_count"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if context.orders_today >= self.max_orders_per_day:
            return [f"maximum daily order count ({self.max_orders_per_day}) reached"]
        return []


class OpenOrderCheck(BaseRiskCheck):
    """Check open order count."""

    def __init__(self, max_open_orders: int = 20) -> None:
        self.max_open_orders = max_open_orders
        self.name = "open_order_count"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if context.open_orders >= self.max_open_orders:
            return [f"maximum open order count ({self.max_open_orders}) reached"]
        return []


class AccountAllowListCheck(BaseRiskCheck):
    """Check account allow list."""

    def __init__(self) -> None:
        self.name = "account_allow_list"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if not context.account_allowed:
            return ["account is not in the configured trading allow-list"]
        return []


class KillSwitchCheck(BaseRiskCheck):
    """Check kill switch."""

    def __init__(self, kill_switch: bool = False) -> None:
        self.kill_switch = kill_switch
        self.name = "kill_switch"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if self.kill_switch:
            return ["global kill switch is active"]
        return []
