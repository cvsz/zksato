from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
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


class TfexContractMetadata(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    series: str = Field(default="", max_length=32)
    underlying: str | None = Field(default=None, max_length=32)
    multiplier: float = Field(default=1.0, gt=0)
    tick_size: float = Field(default=0.1, gt=0)
    expiry: datetime | None = None
    settlement_type: str = Field(default="cash", min_length=1, max_length=32)
    source: str = Field(default="operator", min_length=1, max_length=64)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class TfexContractRegistry:
    def __init__(self, metadata_json: str = "") -> None:
        self._items: dict[str, TfexContractMetadata] = {}
        if metadata_json.strip():
            self.load_json(metadata_json)

    def load_json(self, payload: str) -> None:
        raw = json.loads(payload)
        rows = raw if isinstance(raw, list) else raw.get("contracts", [])
        if not isinstance(rows, list):
            raise ValueError("TFEX contract metadata must be a list")
        for row in rows:
            self.upsert(TfexContractMetadata.model_validate(row))

    def upsert(self, metadata: TfexContractMetadata) -> TfexContractMetadata:
        self._items[metadata.symbol] = metadata
        return metadata

    def get(self, symbol: str) -> TfexContractMetadata | None:
        return self._items.get(symbol.upper())

    def list(self) -> list[TfexContractMetadata]:
        return sorted(self._items.values(), key=lambda item: item.symbol)


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
    dynamic_margin_multiplier: float = Field(default=1.0, ge=1.0)
    market_session_known: bool = True
    market_data_available: bool = True
    contract_metadata_available: bool = True
    tick_size_ok: bool = True
    days_to_expiry: float | None = None


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
        intent = submission.intent
        reasons: list[str] = []
        opening = intent.position != TfexPosition.CLOSE
        if self.settings.kill_switch:
            reasons.append("global kill switch is active")
        if not context.market_session_known:
            reasons.append("market session state is unknown")
        if not context.market_data_available:
            reasons.append("trusted market data is unavailable")
        if self.settings.strict_tfex_reference_data and not context.contract_metadata_available:
            reasons.append("trusted TFEX contract metadata is unavailable")
        if not context.tick_size_ok:
            reasons.append("TFEX limit price is not aligned to contract tick size")
        projected_contracts = context.current_contracts + (intent.volume if opening else 0)
        if projected_contracts > self.settings.max_tfex_contracts:
            reasons.append("maximum TFEX contract exposure exceeded")
        adjusted_margin_usage = (
            context.margin_usage_pct_after_trade * context.dynamic_margin_multiplier
        )
        if adjusted_margin_usage > self.settings.max_tfex_margin_usage_pct:
            reasons.append("TFEX margin usage exceeds configured maximum")
        if (
            opening
            and context.days_to_expiry is not None
            and context.days_to_expiry <= self.settings.tfex_expiry_restriction_days
        ):
            reasons.append("TFEX contract is inside the configured expiry restriction window")
        if (
            context.quote_age_seconds is not None
            and context.quote_age_seconds > self.settings.market_data_stale_seconds
        ):
            reasons.append("market quote is stale")
        return TfexRiskDecision(approved=not reasons, reasons=reasons)


def settlement_pnl(
    previous_settlement: float,
    current_settlement: float,
    net_contracts: int,
    multiplier: float,
) -> float:
    if previous_settlement <= 0 or current_settlement <= 0 or multiplier <= 0:
        raise ValueError("settlement prices and multiplier must be positive")
    return (current_settlement - previous_settlement) * net_contracts * multiplier


def generate_rollover_intents(
    symbol_from: str,
    symbol_to: str,
    current_volume: int,
    position_type: TfexSide,
    close_price: float,
    open_price: float,
) -> list[TfexOrderIntent]:
    if current_volume <= 0:
        return []
    close_side = TfexSide.SHORT if position_type == TfexSide.LONG else TfexSide.LONG
    return [
        TfexOrderIntent(
            symbol=symbol_from,
            side=close_side,
            position=TfexPosition.CLOSE,
            volume=current_volume,
            price=close_price,
        ),
        TfexOrderIntent(
            symbol=symbol_to,
            side=position_type,
            position=TfexPosition.OPEN,
            volume=current_volume,
            price=open_price,
        ),
    ]


class SettradeTfexGateway:
    """Dedicated derivatives gateway; never reused as an equity Broker implementation."""

    def __init__(self, settings: Settings) -> None:
        if not settings.settrade_tfex_configured:
            raise RuntimeError("Settrade derivatives credentials are incomplete")
        self.settings = settings
        self.contracts = TfexContractRegistry(settings.tfex_contract_metadata_json)
        try:
            from settrade_v2 import Investor
        except ImportError as exc:
            raise RuntimeError("install zksato[settrade] to use TFEX") from exc

        broker_id = "SANDBOX" if settings.trading_mode == "sandbox" else settings.settrade_broker_id
        app_code = "SANDBOX" if settings.trading_mode == "sandbox" else settings.settrade_app_code

        investor = Investor(
            app_id=settings.settrade_app_id,
            app_secret=settings.settrade_app_secret,
            broker_id=broker_id,
            app_code=app_code,
            is_auto_queue=False,
        )
        self.derivatives = investor.Derivatives(account_no=settings.settrade_derivatives_account_no)

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

    def contract_metadata(self, symbol: str) -> TfexContractMetadata | None:
        return self.contracts.get(symbol)

    async def risk_context(
        self,
        *,
        symbol: str = "",
        price: float = 0.0,
        quote_age_seconds: float | None,
        market_data_available: bool,
    ) -> TfexRiskContext:
        account, positions = await asyncio.gather(self.account(), self.portfolio())
        current_contracts = 0
        for row in positions:
            long_qty = self._number(
                row,
                "actualLongPosition",
                "longPosition",
                "actualLongQty",
                "longQty",
            )
            short_qty = self._number(
                row,
                "actualShortPosition",
                "shortPosition",
                "actualShortQty",
                "shortQty",
            )
            if long_qty is None and short_qty is None:
                generic = self._number(row, "qty", "volume", "actualVolume") or 0
                current_contracts += abs(int(generic))
            else:
                current_contracts += abs(int(long_qty or 0)) + abs(int(short_qty or 0))

        margin_usage = self._number(
            account,
            "marginUsagePct",
            "marginUtilizationPct",
            "marginUtilization",
        )
        if margin_usage is None:
            margin = self._number(account, "totalMargin", "margin", "initialMargin")
            equity = self._number(account, "equity", "totalEquity", "balance")
            margin_usage = (margin / equity * 100) if margin and equity and equity > 0 else 0.0

        metadata = self.contracts.get(symbol) if symbol else None
        tick_size_ok = True
        days_to_expiry: float | None = None
        if metadata is not None:
            if price > 0:
                units = price / metadata.tick_size
                tick_size_ok = abs(units - round(units)) <= 1e-7
            if metadata.expiry is not None:
                expiry = metadata.expiry
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=UTC)
                days_to_expiry = (expiry - datetime.now(UTC)).total_seconds() / 86_400

        return TfexRiskContext(
            quote_age_seconds=quote_age_seconds,
            current_contracts=max(current_contracts, 0),
            margin_usage_pct_after_trade=max(float(margin_usage or 0), 0.0),
            market_session_known=True,
            market_data_available=market_data_available,
            contract_metadata_available=metadata is not None,
            tick_size_ok=tick_size_ok,
            days_to_expiry=days_to_expiry,
        )

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

    @staticmethod
    def _number(data: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = data.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None
