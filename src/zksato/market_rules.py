from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
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
    """Timezone-aware recurring sessions with operator-supplied holiday/special-date overrides."""

    def __init__(
        self,
        timezone_name: str,
        sessions: str,
        holidays: str = "",
        special_sessions_json: str = "",
    ) -> None:
        try:
            self.timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown market timezone: {timezone_name}") from exc
        self.sessions = self._parse_sessions(sessions)
        self.holidays = self._parse_holidays(holidays)
        self.special_sessions = self._parse_special_sessions(special_sessions_json)

    def state(self, now: datetime | None = None) -> tuple[bool, bool]:
        current = now or datetime.now(UTC)
        try:
            local = current.astimezone(self.timezone)
        except (ValueError, OverflowError):
            return False, False
        sessions, closed = self._sessions_for_date(local.date())
        if closed:
            return True, False
        current_time = local.timetz().replace(tzinfo=None)
        return True, any(start <= current_time <= end for start, end in sessions)

    def explain(self, now: datetime | None = None) -> dict[str, object]:
        current = now or datetime.now(UTC)
        try:
            local = current.astimezone(self.timezone)
        except (ValueError, OverflowError):
            return {
                "known": False,
                "open": False,
                "timezone": str(self.timezone),
                "reason": "invalid current time",
                "sessions": [],
            }
        day = local.date()
        sessions, closed = self._sessions_for_date(day)
        if day in self.special_sessions:
            source = "special"
            reason = "special session override" if sessions else "special closed date"
        elif day in self.holidays:
            source = "holiday"
            reason = "configured market holiday"
        elif day.weekday() >= 5:
            source = "weekend"
            reason = "weekend"
        else:
            source = "default"
            reason = "inside configured session" if not closed else "closed"
        current_time = local.timetz().replace(tzinfo=None)
        is_open = False if closed else any(start <= current_time <= end for start, end in sessions)
        if not is_open and not closed and source in {"default", "special"}:
            reason = "outside configured session"
        return {
            "known": True,
            "open": is_open,
            "timezone": str(self.timezone),
            "local_time": local.isoformat(),
            "date": day.isoformat(),
            "source": source,
            "reason": reason,
            "holiday": day in self.holidays,
            "sessions": [
                f"{start.isoformat(timespec='minutes')}-{end.isoformat(timespec='minutes')}"
                for start, end in sessions
            ],
        }

    def _sessions_for_date(self, day: date) -> tuple[list[tuple[time, time]], bool]:
        if day in self.special_sessions:
            sessions = self.special_sessions[day]
            return sessions, not sessions
        if day in self.holidays or day.weekday() >= 5:
            return [], True
        return self.sessions, False

    @staticmethod
    def _parse_holidays(raw: str) -> set[date]:
        holidays: set[date] = set()
        for item in raw.replace(";", ",").split(","):
            chunk = item.strip()
            if not chunk:
                continue
            try:
                holidays.add(date.fromisoformat(chunk))
            except ValueError as exc:
                raise ValueError(f"invalid market holiday date: {chunk}") from exc
        return holidays

    @classmethod
    def _parse_special_sessions(cls, raw: str) -> dict[date, list[tuple[time, time]]]:
        if not raw.strip():
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("special market sessions must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("special market sessions must be a JSON object keyed by date")
        result: dict[date, list[tuple[time, time]]] = {}
        for raw_day, raw_sessions in payload.items():
            if not isinstance(raw_day, str):
                raise ValueError("special market session date keys must be strings")
            try:
                day = date.fromisoformat(raw_day)
            except ValueError as exc:
                raise ValueError(f"invalid special market session date: {raw_day}") from exc
            if raw_sessions is None:
                result[day] = []
                continue
            if isinstance(raw_sessions, str):
                session_text = raw_sessions
            elif isinstance(raw_sessions, list) and all(
                isinstance(item, str) for item in raw_sessions
            ):
                session_text = ",".join(raw_sessions)
            else:
                raise ValueError(
                    f"special sessions for {raw_day} must be a string, list of strings, or null"
                )
            result[day] = cls._parse_sessions(session_text, allow_empty=True)
        return result

    @staticmethod
    def _parse_sessions(raw: str, *, allow_empty: bool = False) -> list[tuple[time, time]]:
        sessions: list[tuple[time, time]] = []
        for item in raw.split(","):
            chunk = item.strip()
            if not chunk:
                continue
            start_raw, separator, end_raw = chunk.partition("-")
            if not separator:
                raise ValueError(f"invalid market session: {chunk}")
            try:
                start = time.fromisoformat(start_raw.strip())
                end = time.fromisoformat(end_raw.strip())
            except ValueError as exc:
                raise ValueError(f"invalid market session: {chunk}") from exc
            if end <= start:
                raise ValueError(f"market session end must follow start: {chunk}")
            sessions.append((start, end))
        if not sessions and not allow_empty:
            raise ValueError("at least one market session is required")
        return sessions
