from __future__ import annotations

import json
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class InstrumentMetadata(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    asset_class: str = Field(default="equity", min_length=1, max_length=32)
    sector: str | None = Field(default=None, max_length=64)
    tick_size: float | None = Field(default=None, gt=0)
    lower_price_band: float | None = Field(default=None, gt=0)
    upper_price_band: float | None = Field(default=None, gt=0)
    contract_multiplier: float | None = Field(default=None, gt=0)
    expiry: datetime | None = None
    series: str | None = Field(default=None, max_length=32)
    source: str = Field(default="operator", min_length=1, max_length=64)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class InstrumentRegistry:
    """Trusted reference-data registry loaded from operator-supplied JSON."""

    def __init__(self, metadata_json: str = "") -> None:
        self._items: dict[str, InstrumentMetadata] = {}
        if metadata_json.strip():
            self.load_json(metadata_json)

    def load_json(self, payload: str) -> None:
        raw = json.loads(payload)
        rows = raw if isinstance(raw, list) else raw.get("instruments", [])
        if not isinstance(rows, list):
            raise ValueError("instrument metadata must be a list")
        for row in rows:
            self.upsert(InstrumentMetadata.model_validate(row))

    def upsert(self, metadata: InstrumentMetadata) -> InstrumentMetadata:
        self._items[metadata.symbol] = metadata
        return metadata

    def get(self, symbol: str) -> InstrumentMetadata | None:
        return self._items.get(symbol.upper())

    def list(self) -> list[InstrumentMetadata]:
        return sorted(self._items.values(), key=lambda item: item.symbol)

    def validate_price(self, symbol: str, price: float | None) -> tuple[bool, bool, bool]:
        metadata = self.get(symbol)
        if metadata is None or price is None:
            return metadata is not None, True, True
        band_ok = True
        if metadata.lower_price_band is not None and price < metadata.lower_price_band:
            band_ok = False
        if metadata.upper_price_band is not None and price > metadata.upper_price_band:
            band_ok = False
        tick_ok = True
        if metadata.tick_size:
            units = price / metadata.tick_size
            tick_ok = abs(units - round(units)) <= 1e-7
        return True, band_ok, tick_ok

    def sector_for(self, symbol: str) -> str | None:
        metadata = self.get(symbol)
        return metadata.sector if metadata else None


class MarketSessionPolicy:
    def __init__(self, timezone_name: str, sessions: str) -> None:
        try:
            self.timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown market timezone: {timezone_name}") from exc
        self.sessions = self._parse_sessions(sessions)

    def state(self, now: datetime | None = None) -> tuple[bool, bool]:
        current = now or datetime.now(UTC)
        try:
            local = current.astimezone(self.timezone)
        except (ValueError, OverflowError):
            return False, False
        if local.weekday() >= 5:
            return True, False
        current_time = local.timetz().replace(tzinfo=None)
        return True, any(start <= current_time <= end for start, end in self.sessions)

    @staticmethod
    def _parse_sessions(raw: str) -> list[tuple[time, time]]:
        sessions: list[tuple[time, time]] = []
        for item in raw.split(","):
            chunk = item.strip()
            if not chunk:
                continue
            start_raw, separator, end_raw = chunk.partition("-")
            if not separator:
                raise ValueError(f"invalid market session: {chunk}")
            start = time.fromisoformat(start_raw.strip())
            end = time.fromisoformat(end_raw.strip())
            if end <= start:
                raise ValueError(f"market session end must follow start: {chunk}")
            sessions.append((start, end))
        if not sessions:
            raise ValueError("at least one market session is required")
        return sessions
