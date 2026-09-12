from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from zksato.domain import OrderIntent, OrderType, RiskDecision, Side


class ZTraderScores(BaseModel):
    opportunity: int = Field(ge=0, le=100)
    risk: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)


class ZTraderProposedTrade(BaseModel):
    mode: Literal["paper"] = "paper"
    side: Side
    order_type: Literal["limit"] = "limit"
    entry_low: float | None = Field(default=None, gt=0)
    entry_high: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit_levels: list[float] = Field(default_factory=list)
    max_position_usd: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_entry(self) -> "ZTraderProposedTrade":
        if self.entry_low is None and self.entry_high is None:
            raise ValueError("paper advisory intent requires entry_low or entry_high")
        if (
            self.entry_low is not None
            and self.entry_high is not None
            and self.entry_low > self.entry_high
        ):
            raise ValueError("entry_low must not exceed entry_high")
        return self

    def reference_price(self) -> float:
        if self.entry_low is not None and self.entry_high is not None:
            return (self.entry_low + self.entry_high) / 2
        return float(self.entry_low or self.entry_high or 0)


class ZTraderAdvisoryIntent(BaseModel):
    version: Literal["1.1"]
    tenant_id: str = Field(min_length=1, max_length=128)
    account_ref: str = Field(min_length=1, max_length=256)
    portfolio_ref: str | None = Field(default=None, max_length=256)
    signal_id: str = Field(min_length=1, max_length=128)
    trace_id: str | None = Field(default=None, max_length=128)
    symbol: str = Field(min_length=1, max_length=64)
    chain: str = Field(min_length=1, max_length=64)
    address: str = Field(min_length=1, max_length=256)
    scores: ZTraderScores
    narrative: Literal["EARLY", "HEATING_UP", "CROWDED", "FADING", "DEAD"]
    whales: Literal["ACCUMULATING", "NEUTRAL", "DISTRIBUTING"]
    rug_risk: Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
    action: Literal["WATCH", "WAIT", "RESEARCH_MORE", "AVOID"]
    evidence_timestamp: datetime
    invalidations: list[str] = Field(default_factory=list)
    proposed_trade: ZTraderProposedTrade
    evidence: dict[str, object] = Field(default_factory=dict)

    def to_order_intent(self) -> OrderIntent:
        price = self.proposed_trade.reference_price()
        quantity = self.proposed_trade.max_position_usd / price
        take_profit = (
            self.proposed_trade.take_profit_levels[0]
            if self.proposed_trade.take_profit_levels
            else None
        )
        return OrderIntent(
            symbol=self.symbol,
            side=self.proposed_trade.side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            price=price,
            stop_loss=self.proposed_trade.stop_loss,
            take_profit=take_profit,
            client_order_id=f"ztrader:{self.signal_id}"[:128],
            source="ztrader-intel",
        )


class ZTraderPreflightResponse(BaseModel):
    trace_id: str | None = None
    mode: Literal["paper"] = "paper"
    live_execution_allowed: Literal[False] = False
    intent: OrderIntent
    decision: RiskDecision
