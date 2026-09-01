"""UAT integration tests for Settrade Open API v2.

These tests require real broker-provided UAT credentials and are excluded from
normal CI by the ``uat`` marker. They must never log or expose secrets.

Settrade sandbox availability:
- Best availability: Thursday and Friday, 09:00-17:00 Thailand time
- Supports Equity (Day Session) and Derivatives (Day & Night Session)
- Does NOT support Offline Order
- No guarantee outside the above hours
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv

from zksato.broker.settrade import SettradeBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderType, Side

load_dotenv()

_BKK = timezone(timedelta(hours=7))


def _now_bkk() -> datetime:
    return datetime.now(_BKK)


def _is_uat_available() -> bool:
    now = _now_bkk()
    weekday = now.weekday()  # 0=Mon, 3=Thu, 4=Fri
    if weekday not in (3, 4):
        return False
    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end = now.replace(hour=17, minute=0, second=0, microsecond=0)
    return start <= now <= end


def _uat_settings() -> Settings:
    return Settings(
        environment="uat",
        trading_mode="sandbox",
        settrade_app_id=os.getenv("ZKSATO_SETTRADE_APP_ID", ""),
        settrade_app_secret=os.getenv("ZKSATO_SETTRADE_APP_SECRET", ""),
        settrade_broker_id=os.getenv("ZKSATO_SETTRADE_BROKER_ID", "SANDBOX"),
        settrade_app_code=os.getenv("ZKSATO_SETTRADE_APP_CODE", "SANDBOX"),
        settrade_account_no=os.getenv("ZKSATO_SETTRADE_ACCOUNT_NO", ""),
        settrade_pin=os.getenv("ZKSATO_SETTRADE_PIN", ""),
    )


def _require_uat_credentials(settings: Settings) -> None:
    if not settings.settrade_configured:
        pytest.skip("Settrade UAT credentials are not configured")


def _require_uat_availability() -> None:
    if not _is_uat_available():
        now = _now_bkk().strftime("%Y-%m-%d %H:%M:%S %Z")
        pytest.skip(
            f"Settrade sandbox is not guaranteed outside Thu/Fri "
            f"09:00-17:00 Thailand time. Current time: {now}"
        )


def _assert_valid_uat_credentials(settings: Settings) -> None:
    _require_uat_credentials(settings)
    try:
        SettradeBroker(settings=settings)
    except Exception as exc:
        msg = str(exc)
        if "User not found" in msg:
            pytest.fail(
                "Settrade UAT credentials are invalid or expired. "
                "Obtain valid UAT credentials from "
                "https://developer.settrade.com/open-api/api-reference "
                "and update .env with working ZKSATO_SETTRADE_* values."
            )
        raise


@pytest.mark.uat
@pytest.mark.asyncio
async def test_uat_account_lookup() -> None:
    settings = _uat_settings()
    _require_uat_availability()
    _assert_valid_uat_credentials(settings)

    broker = SettradeBroker(settings=settings)
    account = await broker.account()
    assert account is not None
    assert "cashBalance" in account or "cash_balance" in account


@pytest.mark.uat
@pytest.mark.asyncio
async def test_uat_portfolio_lookup() -> None:
    settings = _uat_settings()
    _require_uat_availability()
    _assert_valid_uat_credentials(settings)

    broker = SettradeBroker(settings=settings)
    portfolio = await broker.portfolio()
    assert portfolio is not None
    assert "positions" in portfolio or "holdings" in portfolio


@pytest.mark.uat
@pytest.mark.asyncio
async def test_uat_limit_buy_and_cancel() -> None:
    settings = _uat_settings()
    _require_uat_availability()
    _assert_valid_uat_credentials(settings)

    broker = SettradeBroker(settings=settings)
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=50.0,
        client_order_id="uat-test-buy",
    )
    record = await broker.place_order(intent)
    assert record.status.value == "accepted"
    assert record.broker_order_id is not None

    cancelled = await broker.cancel_order(record.broker_order_id)
    assert cancelled.status.value == "cancelled"


@pytest.mark.uat
@pytest.mark.asyncio
async def test_uat_order_rejection_returns_understandable_error() -> None:
    settings = _uat_settings()
    _require_uat_availability()
    _assert_valid_uat_credentials(settings)

    broker = SettradeBroker(settings=settings)
    intent = OrderIntent(
        symbol="INVALID_SYMBOL_ZZZ",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=50.0,
        client_order_id="uat-test-reject",
    )
    with pytest.raises(Exception) as exc_info:
        await broker.place_order(intent)

    exc = exc_info.value
    assert hasattr(exc, "code") or hasattr(exc, "status_code"), (
        f"Expected SettradeError with code/status_code, got {type(exc).__name__}: {exc}"
    )
    if hasattr(exc, "code"):
        assert exc.code is not None
    if hasattr(exc, "status_code"):
        assert exc.status_code is not None


@pytest.mark.uat
@pytest.mark.asyncio
async def test_uat_duplicate_client_order_id_is_idempotent() -> None:
    settings = _uat_settings()
    _require_uat_availability()
    _assert_valid_uat_credentials(settings)

    broker = SettradeBroker(settings=settings)
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        price=50.0,
        client_order_id="uat-test-idempotent",
    )
    first = await broker.place_order(intent)
    second = await broker.place_order(intent)
    assert second.id == first.id
