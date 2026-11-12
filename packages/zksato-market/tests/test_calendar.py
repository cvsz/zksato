"""Tests for zksato-market calendar."""

import pytest
from datetime import date, datetime, time

from zksato_market.calendar import TradingCalendar
from zksato_market.types import MarketType
from zksato_core.datetime import MarketSession, BANGKOK_TZ


def test_trading_calendar_creation():
    cal = TradingCalendar.create_default()
    assert cal.equity_calendar is not None
    assert cal.tfex_calendar is not None


def test_trading_calendar_with_holidays():
    holiday = date(2026, 1, 1)
    cal = TradingCalendar.create_default(equity_holidays=[holiday])
    assert not cal.is_trading_day(holiday, MarketType.EQUITY)
    assert cal.is_trading_day(date(2026, 1, 2), MarketType.EQUITY)


def test_is_session_open():
    cal = TradingCalendar.create_default()

    # Monday 10:00 Bangkok time
    dt = datetime(2026, 1, 5, 10, 0, 0, tzinfo=BANGKOK_TZ)  # Monday
    assert cal.is_session_open(dt, MarketType.EQUITY) is True

    # Monday 13:00 Bangkok time (lunch break)
    dt = datetime(2026, 1, 5, 13, 0, 0, tzinfo=BANGKOK_TZ)
    assert cal.is_session_open(dt, MarketType.EQUITY) is False

    # Monday 14:30 Bangkok time (afternoon session)
    dt = datetime(2026, 1, 5, 14, 30, 0, tzinfo=BANGKOK_TZ)
    assert cal.is_session_open(dt, MarketType.EQUITY) is True

    # Saturday
    dt = datetime(2026, 1, 3, 10, 0, 0, tzinfo=BANGKOK_TZ)
    assert cal.is_session_open(dt, MarketType.EQUITY) is False


def test_tfex_sessions():
    cal = TradingCalendar.create_default()

    # TFEX day session
    dt = datetime(2026, 1, 5, 10, 0, 0, tzinfo=BANGKOK_TZ)
    assert cal.is_session_open(dt, MarketType.TFEX) is True

    # TFEX night session
    dt = datetime(2026, 1, 5, 20, 0, 0, tzinfo=BANGKOK_TZ)
    assert cal.is_session_open(dt, MarketType.TFEX) is True


def test_get_sessions():
    cal = TradingCalendar.create_default()
    sessions = cal.get_sessions(date(2026, 1, 5), MarketType.EQUITY)
    assert len(sessions) == 2
    assert sessions[0].name == "morning"
    assert sessions[1].name == "afternoon"

    tfex_sessions = cal.get_sessions(date(2026, 1, 5), MarketType.TFEX)
    assert len(tfex_sessions) == 2
    assert tfex_sessions[0].name == "tfex_day"
    assert tfex_sessions[1].name == "tfex_night"


def test_next_session_open():
    cal = TradingCalendar.create_default()

    # After market close
    dt = datetime(2026, 1, 5, 17, 0, 0, tzinfo=BANGKOK_TZ)
    next_open = cal.next_session_open(dt, MarketType.EQUITY)
    assert next_open is not None
    assert next_open.date() == date(2026, 1, 6)
    assert next_open.hour == 9
    assert next_open.minute == 30