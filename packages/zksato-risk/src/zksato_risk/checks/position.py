"""Position limit checks."""

from __future__ import annotations

from zksato_core.models import OrderIntent, RiskContext, Side
from zksato_risk.checks.base import BaseRiskCheck


class PositionLimitCheck(BaseRiskCheck):
    """Check position count limit."""

    def __init__(self, max_positions: int = 5) -> None:
        self.max_positions = max_positions
        self.name = "position_limit"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if intent.side == Side.BUY and context.opens_new_position:
            if context.current_positions >= self.max_positions:
                return [f"maximum number of positions ({self.max_positions}) reached"]
        return []


class PositionSizeCheck(BaseRiskCheck):
    """Check position size limit."""

    def __init__(self, max_position_pct: float = 10.0) -> None:
        self.max_position_pct = max_position_pct
        self.name = "position_size"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if intent.side == Side.BUY and not context.reduces_exposure:
            if context.position_pct_after_trade > self.max_position_pct:
                return [f"position size exceeds maximum portfolio percentage ({self.max_position_pct}%)"]
        return []


class ConcentrationCheck(BaseRiskCheck):
    """Check symbol/sector concentration."""

    def __init__(self, max_symbol_pct: float = 20.0, max_sector_pct: float = 35.0) -> None:
        self.max_symbol_pct = max_symbol_pct
        self.max_sector_pct = max_sector_pct
        self.name = "concentration"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        reasons: list[str] = []
        if context.symbol_exposure_pct > self.max_symbol_pct:
            reasons.append(f"symbol exposure {context.symbol_exposure_pct:.1f}% exceeds limit {self.max_symbol_pct:.1f}%")
        if context.sector_exposure_pct > self.max_sector_pct:
            reasons.append(f"sector exposure {context.sector_exposure_pct:.1f}% exceeds limit {self.max_sector_pct:.1f}%")
        return reasons


class ShortSellingCheck(BaseRiskCheck):
    """Check short selling restrictions."""

    def __init__(self, allow_short: bool = False) -> None:
        self.allow_short = allow_short
        self.name = "short_selling"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if intent.side == Side.SELL:
            if not self.allow_short and not context.reduces_exposure:
                if context.available_quantity is None or intent.quantity > context.available_quantity:
                    return ["equity short selling is disabled: sell quantity exceeds available position"]
        return []


class BoardLotCheck(BaseRiskCheck):
    """Check SET board lot (100 shares)."""

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict
        self.name = "board_lot"

    def check(self, intent: OrderIntent, context: RiskContext) -> list[str]:
        if self.strict and "/" not in intent.symbol:
            if float(intent.quantity) != int(intent.quantity):
                return ["SET quantity must be integer"]
            elif int(intent.quantity) % 100 != 0:
                return ["SET quantity must be multiple of 100 (board lot)"]
        return []