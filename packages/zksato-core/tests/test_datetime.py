"""Tests for zksato-core datetime module."""

import pytest
from datetime import date, time, timedelta

import pendulum

from zksato_core.datetime import (
    BANGKOK_TZ,
    UTC_TZ,
    now_bangkok,
    now_utc,
    to_bangkok,
    to_utc,
    bangkok_today,
    parse_iso_datetime,
    format_iso_datetime,
    MarketSession,
    MarketCalendar,
    DEFAULT_EQUITY_SESSIONS,
    DEFAULT_TFEX_DAY_SESSION,
    DEFAULT_TFEX_NIGHT_SESSION,
    create_default_calendar,
)


def test_now_bangkok():
    dt = now_bangkok()
    assert dt.tzinfo is not None
    assert dt.tzinfo.key == "Asia/Bangkok"


def test_now_utc():
    dt = now_utc()
    assert dt.tzinfo is not None
    assert dt.tzinfo.key == "UTC"


def test_to_bangkok():
    utc_dt = pendulum.datetime(2026, 1, 1, 12, 0, 0, tz="UTC")
    bkk_dt = to_bangkok(utc_dt)
    assert bkk_dt.tzinfo.key == "Asia/Bangkok"
    # Bangkok is UTC+7
    assert bkk_dt.hour == 19


def test_to_utc():
    bkk_dt = pendulum.datetime(2026, 1, 1, 19, 0, 0, tz="Asia/Bangkok")
    utc_dt = to_utc(bkk_dt)
    assert utc_dt.tzinfo.key == "UTC"
    assert utc_dt.hour == 12


def test_bangkok_today():
    today = bangkok_today()
    assert isinstance(today, date)


def test_parse_iso_datetime():
    dt = parse_iso_datetime("2026-01-01T12:00:00+07:00")
    assert dt.year == 2026
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 12


def test_format_iso_datetime():
    dt = pendulum.datetime(2026, 1, 1, 12, 0, 0, tz="Asia/Bangkok")
    s = format_iso_datetime(dt)
    assert "2026-01-01T12:00:00+07:00" in s


def test_market_session():
    session = MarketSession("test", time(9, 30), time(12, 30))
    dt = pendulum.datetime(2026, 1, 1, 10, 0, 0, tz="Asia/Bangkok")
    assert session.contains(dt) is True

    dt = pendulum.datetime(2026, 1, 1, 13, 0, 0, tz="Asia/Bangkok")
    assert session.contains(dt) is False


def test_default_equity_sessions():
    assert len(DEFAULT_EQUITY_SESSIONS) == 2
    assert DEFAULT_EQUITY_SESSIONS[0].name == "morning"
    assert DEFAULT_EQUITY_SESSIONS[0].start == time(9, 30)
    assert DEFAULT_EQUITY_SESSIONS[0].end == time(12, 30)
    assert DEFAULT_EQUITY_SESSIONS[1].name == "afternoon"
    assert DEFAULT_EQUITY_SESSIONS[1].start == time(14, 0)
    assert DEFAULT_EQUITY_SESSIONS[1].end == time(16, 30)


def test_default_tfex_sessions():
    assert DEFAULT_TFEX_DAY_SESSION.name == "tfex_day"
    assert DEFAULT_TFEX_DAY_SESSION.start == time(9, 30)
    assert DEFAULT_TFEX_DAY_SESSION.end == time(16, 30)
    assert DEFAULT_TFEX_NIGHT_SESSION.name == "tfex_night"
    assert DEFAULT_TFEX_NIGHT_SESSION.start == time(19, 0)
    assert DEFAULT_TFEX_NIGHT_SESSION.end == time(23, 59)


def test_create_default_calendar():
    cal = create_default_calendar()
    assert cal.equity_sessions == DEFAULT_EQUITY_SESSIONS
    assert cal.tfex_day_session == DEFAULT_TFEX_DAY_SESSION
    assert cal.tfex_night_session == DEFAULT_TFEX_NIGHT_SESSION
    assert cal.holidays == set()
    assert cal.special_sessions == {}


def test_calendar_is_holiday():
    holiday = date(2026, 1, 1)
    cal = create_default_calendar(holidays=[holiday])
    assert cal.is_holiday(holiday) is True
    assert cal.is_holiday(date(2026, 1, 2)) is False


def test_calendar_is_trading_day():
    cal = create_default_calendar()
    # Monday
    assert cal.is_trading_day(date(2026, 1, 5)) is True
    # Saturday
    assert cal.is_trading_day(date(2026, 1, 3)) is False
    # Sunday
    assert cal.is_trading_day(date(2026, 1, 4)) is False


def test_calendar_get_sessions():
    cal = create_default_calendar()
    sessions = cal.get_sessions(date(2026, 1, 5), "equity")
    assert len(sessions) == 2

    sessions = cal.get_sessions(date(2026, 1, 5), "tfex")
    assert len(sessions) == 2


def test_calendar_is_session_open():
    cal = create_default_calendar()
    dt = pendulum.datetime(2026, 1, 5, 10, 0, 0, tz="Asia/Bangkok")
    assert cal.is_session_open(dt, "equity") is True

    dt = pendulum.datetime(2026, 1, 5, 13, 0, 0, tz="Asia/Bangkok")
    assert cal.is_session_open(dt, "equity") is False


def test_calendar_special_sessions():
    special_date = date(2026, 12, 31)
    special_session = MarketSession("special", time(9, 30), time(12, 0))
    cal = create_default_calendar(special_sessions={special_date: [special_session]})

    sessions = cal.get_sessions(special_date, "equity")
    assert len(sessions) == 1
    assert sessions[0].name == "special"


def test_calendar_next_session_open():
    cal = create_default_calendar()
    dt = pendulum.datetime(2026, 1, 5, 17, 0, 0, tz="Asia/Bangkok")  # After close
    next_open = cal.next_session_open(dt, "equity")
    assert next_open is not None
    assert next_open.date() == date(2026, 1, 6)
    assert next_open.hour == 9
    assert next_open.minute == 30