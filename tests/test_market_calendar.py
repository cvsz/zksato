from datetime import UTC, datetime

import pytest

from zksato.market_rules import MarketSessionPolicy


def test_configured_holiday_is_closed() -> None:
    policy = MarketSessionPolicy(
        "Asia/Bangkok",
        "09:30-12:30,14:00-16:30",
        holidays="2026-08-10",
    )
    known, is_open = policy.state(datetime(2026, 8, 10, 3, 0, tzinfo=UTC))
    assert known is True
    assert is_open is False
    assert policy.explain(datetime(2026, 8, 10, 3, 0, tzinfo=UTC))["source"] == "holiday"


def test_special_session_can_override_weekend() -> None:
    policy = MarketSessionPolicy(
        "Asia/Bangkok",
        "09:30-12:30,14:00-16:30",
        special_sessions_json='{"2026-08-09":"10:00-11:00"}',
    )
    known, is_open = policy.state(datetime(2026, 8, 9, 3, 30, tzinfo=UTC))
    assert known is True
    assert is_open is True
    explanation = policy.explain(datetime(2026, 8, 9, 3, 30, tzinfo=UTC))
    assert explanation["source"] == "special"
    assert explanation["sessions"] == ["10:00-11:00"]


def test_special_null_marks_date_closed() -> None:
    policy = MarketSessionPolicy(
        "Asia/Bangkok",
        "09:30-12:30,14:00-16:30",
        special_sessions_json='{"2026-08-11":null}',
    )
    known, is_open = policy.state(datetime(2026, 8, 11, 3, 30, tzinfo=UTC))
    assert known is True
    assert is_open is False
    assert policy.explain(datetime(2026, 8, 11, 3, 30, tzinfo=UTC))["source"] == "special"


def test_invalid_calendar_configuration_fails_fast() -> None:
    with pytest.raises(ValueError, match="holiday"):
        MarketSessionPolicy("Asia/Bangkok", "09:30-12:30", holidays="not-a-date")
    with pytest.raises(ValueError, match="valid JSON"):
        MarketSessionPolicy(
            "Asia/Bangkok",
            "09:30-12:30",
            special_sessions_json="{bad-json",
        )
