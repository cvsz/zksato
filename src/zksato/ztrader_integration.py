from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AdvisoryScores(BaseModel):
    opportunity: int = Field(ge=0, le=100)
    risk: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)


class ProposedPaperTrade(BaseModel):
    mode: Literal["paper"] = "paper"
    side: Literal["buy", "sell"]
    order_type: Literal["limit"] = "limit"
    entry_low: float | None = Field(default=None, gt=0)
    entry_high: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit_levels: list[float] = Field(default_factory=list)
    max_position_usd: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_entry_band(self) -> ProposedPaperTrade:
        if (
            self.entry_low is not None
            and self.entry_high is not None
            and self.entry_low > self.entry_high
        ):
            raise ValueError("entry_low must be <= entry_high")
        return self


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
    scores: AdvisoryScores
    narrative: Literal["EARLY", "HEATING_UP", "CROWDED", "FADING", "DEAD"]
    whales: Literal["ACCUMULATING", "NEUTRAL", "DISTRIBUTING"]
    rug_risk: Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
    action: Literal["WATCH", "WAIT", "RESEARCH_MORE", "AVOID"]
    evidence_timestamp: str = Field(min_length=1, max_length=64)
    invalidations: list[str] = Field(default_factory=list)
    proposed_trade: ProposedPaperTrade
    evidence: dict[str, object] = Field(default_factory=dict)


class ZTraderAdvisoryDecision(BaseModel):
    accepted: bool
    execution_allowed: Literal[False] = False
    risk_review_required: bool = True
    signal_id: str
    trace_id: str | None = None
    canonical_executor: Literal["zksato"] = "zksato"
    mode: Literal["paper"] = "paper"
    reason: str


def evaluate_advisory_intent(
    intent: ZTraderAdvisoryIntent,
    *,
    trading_mode: str,
    kill_switch: bool,
) -> ZTraderAdvisoryDecision:
    if trading_mode != "paper":
        return ZTraderAdvisoryDecision(
            accepted=False,
            signal_id=intent.signal_id,
            trace_id=intent.trace_id,
            reason="zTrader advisory intents are accepted only by the paper-trading boundary",
        )

    if kill_switch:
        reason = "advisory recorded; execution remains blocked by the zksato kill switch"
    elif intent.action in {"AVOID", "RESEARCH_MORE"}:
        reason = "advisory recorded; action is non-executable and requires further review"
    else:
        reason = "advisory recorded for deterministic zksato risk review"

    return ZTraderAdvisoryDecision(
        accepted=True,
        signal_id=intent.signal_id,
        trace_id=intent.trace_id,
        reason=reason,
    )
