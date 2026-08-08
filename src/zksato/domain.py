from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    LIMIT = "limit"
    MARKET = "market"


class OrderStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FILLED = "filled"


class OrderIntent(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: Side
    quantity: int = Field(gt=0)
    order_type: OrderType = OrderType.LIMIT
    price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    client_order_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_price(self) -> OrderIntent:
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("price is required for limit orders")
        return self


class RiskContext(BaseModel):
    current_positions: int = Field(default=0, ge=0)
    daily_pnl_pct: float = 0.0
    drawdown_pct: float = Field(default=0.0, ge=0)
    position_pct_after_trade: float = Field(default=0.0, ge=0, le=100)
    line_available: float | None = Field(default=None, ge=0)


class OrderSubmission(BaseModel):
    intent: OrderIntent
    risk: RiskContext = Field(default_factory=RiskContext)


class RiskDecision(BaseModel):
    approved: bool
    reasons: list[str] = Field(default_factory=list)


class OrderRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    client_order_id: str | None = None
    symbol: str
    side: Side
    quantity: int
    order_type: OrderType
    price: float | None
    status: OrderStatus
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
