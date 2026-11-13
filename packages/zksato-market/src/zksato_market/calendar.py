"""Market calendar, sessions, holidays."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from zksato_core.datetime import MarketCalendar, MarketSession, create_default_calendar

from zksato_market.types import MarketType


@dataclass
class TradingCalendar:
    """Trading calendar with market-specific sessions."""

    equity_calendar: MarketCalendar
    tfex_calendar: MarketCalendar

    @classmethod
    def create_default(
        cls,
        equity_holidays: list[date] | None = None,
        tfex_holidays: list[date] | None = None,
        equity_special: dict[date, list[MarketSession]] | None = None,
        tfex_special: dict[date, list[MarketSession]] | None = None,
    ) -> TradingCalendar:
        """Create default trading calendar."""
        equity_cal = create_default_calendar(
            holidays=equity_holidays or [],
            special_sessions=equity_special or {},
        )

        # TFEX uses different sessions
        tfex_sessions = [
            MarketSession("tfex_day", time(9, 30), time(16, 30)),
            MarketSession("tfex_night", time(19, 0), time(23, 59)),
        ]

        tfex_cal = MarketCalendar(
            equity_sessions=tfex_sessions,
            tfex_day_session=tfex_sessions[0],
            tfex_night_session=tfex_sessions[1],
            holidays=set(tfex_holidays or []),
            special_sessions=tfex_special or {},
        )

        return cls(equity_calendar=equity_cal, tfex_calendar=tfex_cal)

    def is_trading_day(self, dt: date, market: MarketType = MarketType.EQUITY) -> bool:
        """Check if date is a trading day."""
        if market == MarketType.EQUITY:
            return self.equity_calendar.is_trading_day(dt)
        elif market == MarketType.TFEX:
            return self.tfex_calendar.is_trading_day(dt)
        return True

    def is_session_open(
        self,
        dt: datetime,
        market: MarketType = MarketType.EQUITY,
    ) -> bool:
        """Check if market session is open."""
        if market == MarketType.EQUITY:
            return self.equity_calendar.is_session_open(dt, "equity")
        elif market == MarketType.TFEX:
            return self.tfex_calendar.is_session_open(dt, "tfex")
        return False

    def get_sessions(
        self,
        dt: date,
        market: MarketType = MarketType.EQUITY,
    ) -> list[MarketSession]:
        """Get trading sessions for date."""
        if market == MarketType.EQUITY:
            return self.equity_calendar.get_sessions(dt, "equity")
        elif market == MarketType.TFEX:
            return self.tfex_calendar.get_sessions(dt, "tfex")
        return []

    def next_session_open(
        self,
        dt: datetime,
        market: MarketType = MarketType.EQUITY,
    ) -> datetime | None:
        """Get next session open time."""
        if market == MarketType.EQUITY:
            return self.equity_calendar.next_session_open(dt, "equity")
        elif market == MarketType.TFEX:
            return self.tfex_calendar.next_session_open(dt, "tfex")
        return None
