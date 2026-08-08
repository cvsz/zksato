from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from zksato.config import Settings


class TfexSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class TfexPosition(StrEnum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    AUTO = "AUTO"


class TfexOrderIntent(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: TfexSide
    position: TfexPosition
    volume: int = Field(gt=0)
    price: float = Field(default=0, ge=0)
    price_type: str = "LIMIT"
    validity_type: str = "GOOD_TILL_DAY"
    stop_condition: str = ""
    stop_price: float = Field(default=0, ge=0)
    stop_symbol: str = ""
    bypass_warning: bool = False

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_limit_price(self) -> TfexOrderIntent:
        if self.price_type.upper() == "LIMIT" and self.price <= 0:
            raise ValueError("positive price is required for TFEX LIMIT orders")
        return self


class TfexRiskContext(BaseModel):
    quote_age_seconds: float | None = Field(default=None, ge=0)
    current_contracts: int = Field(default=0, ge=0)
    margin_usage_pct_after_trade: float = Field(default=0, ge=0)
    market_session_known: bool = True


class TfexRiskDecision(BaseModel):
    approved: bool
    reasons: list[str] = Field(default_factory=list)


class TfexOrderSubmission(BaseModel):
    intent: TfexOrderIntent
    risk: TfexRiskContext = Field(default_factory=TfexRiskContext)


class TfexRiskEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, submission: TfexOrderSubmission) -> TfexRiskDecision:
        context = submission.risk
        reasons: list[str] = []
        if self.settings.kill_switch:
            reasons.append("global kill switch is active")
        if not context.market_session_known:
            reasons.append("market session state is unknown")
        if context.current_contracts + submission.intent.volume > self.settings.max_tfex_contracts:
            reasons.append("maximum TFEX contract exposure exceeded")
        if context.margin_usage_pct_after_trade > self.settings.max_tfex_margin_usage_pct:
            reasons.append("TFEX margin usage exceeds configured maximum")
        if (
            context.quote_age_seconds is not None
            and context.quote_age_seconds > self.settings.market_data_stale_seconds
        ):
            reasons.append("market quote is stale")
        return TfexRiskDecision(approved=not reasons, reasons=reasons)


class SettradeTfexGateway:
    """Dedicated derivatives gateway; never reused as an equity Broker implementation."""

    def __init__(self, settings: Settings) -> None:
        if not settings.settrade_tfex_configured:
            raise RuntimeError("Settrade derivatives credentials are incomplete")
        self.settings = settings
        try:
            from settrade_v2 import Investor  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("install zksato[settrade] to use TFEX") from exc
        investor = Investor(
            app_id=settings.settrade_app_id,
            app_secret=settings.settrade_app_secret,
            broker_id=settings.settrade_broker_id,
            app_code=settings.settrade_app_code,
            is_auto_queue=False,
        )
        self.derivatives = investor.Derivatives(
            account_no=settings.settrade_derivatives_account_no
        )

    async def account(self) -> dict[str, Any]:
        return await asyncio.to_thread(self.derivatives.get_account_info)

    async def portfolio(self) -> list[dict[str, Any]]:
        getter = getattr(self.derivatives, "get_portfolios", None)
        if getter is None:
            raise RuntimeError("installed Settrade SDK does not expose TFEX get_portfolios")
        rows = await asyncio.to_thread(getter)
        return list(rows or [])

    async def orders(self) -> list[dict[str, Any]]:
        rows = await asyncio.to_thread(self.derivatives.get_orders)
        return list(rows or [])

    async def place_uat_order(self, intent: TfexOrderIntent) -> dict[str, Any]:
        if self.settings.trading_mode != "sandbox":
            raise RuntimeError("TFEX mutation is restricted to sandbox/UAT")
        try:
            payload = await asyncio.to_thread(
                self.derivatives.place_order,
                symbol=intent.symbol,
                price=intent.price,
                volume=intent.volume,
                side=intent.side.value,
                position=intent.position.value,
                pin=self.settings.settrade_pin,
                price_type=intent.price_type,
                stop_condition=intent.stop_condition,
                stop_price=intent.stop_price,
                stop_symbol=intent.stop_symbol,
                validity_type=intent.validity_type,
                bypass_warning=intent.bypass_warning,
            )
        except TypeError as exc:
            raise RuntimeError(
                "installed Settrade SDK TFEX place_order signature differs; certify in UAT"
            ) from exc
        if not isinstance(payload, dict):
            return {"result": payload}
        return payload
