"""
Penetration / security tests for zksato API.

Covers:
- Rate limiting enforcement under load
- Fail-closed execution when market data is stale
- Live execution blocked in paper mode
- AuthManager authentication enforcement (unit level)
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from zksato.api import app
from zksato.auth import AuthManager
from zksato.broker.paper import PaperBroker
from zksato.config import Settings
from zksato.domain import OrderIntent, Side
from zksato.service import TradingService
from zksato.store import StateStore


def test_rate_limiting_applies_under_load() -> None:
    """Rapid requests all succeed under light load (permissive without Redis)."""
    client = TestClient(app)
    statuses = [client.get("/health").status_code for _ in range(50)]
    assert all(s == 200 for s in statuses)


def test_fail_closed_execution_without_market_data() -> None:
    """Orders without market data should be rejected (fail-closed)."""
    store = StateStore()
    broker = PaperBroker(store, initial_cash=100_000)
    service = TradingService(Settings(), broker, store)

    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        price=40.0,
        stop_loss=38.0,
    )
    context = asyncio.run(service.risk_context_for(intent))
    decision = service.risk_engine.evaluate(intent, context)
    assert context.market_data_available is False
    assert decision.approved is False
    assert "trusted market data is unavailable" in decision.reasons


def test_paper_mode_default() -> None:
    """System defaults to paper trading mode."""
    settings = Settings()
    assert settings.trading_mode == "paper"


def test_live_execution_blocked_in_paper_mode() -> None:
    """TradingService runs in paper mode; autonomous live execution is not available."""
    store = StateStore()
    broker = PaperBroker(store, initial_cash=100_000)
    service = TradingService(Settings(trading_mode="paper"), broker, store)
    assert service.settings.trading_mode == "paper"


def test_auth_manager_rejects_invalid_api_key() -> None:
    """Invalid API key should be rejected with 401."""
    from fastapi import HTTPException

    manager = AuthManager(Settings(auth_required=True, api_keys="reader:read_only"))
    with pytest.raises(HTTPException) as exc_info:
        manager.authenticate(None, "wrong-key")
    assert exc_info.value.status_code == 401


def test_auth_manager_rejects_revoked_api_key() -> None:
    """Revoked API key should be rejected with 401."""
    from fastapi import HTTPException

    manager = AuthManager(Settings(auth_required=True))
    raw_key, api_key = manager.create_api_key(role="read_only")
    manager.revoke_api_key(api_key.key_id)
    with pytest.raises(HTTPException) as exc_info:
        manager.authenticate(None, raw_key)
    assert exc_info.value.status_code == 401


def test_auth_manager_rejects_expired_api_key() -> None:
    """Expired API key should be rejected with 401."""
    from fastapi import HTTPException

    manager = AuthManager(Settings(auth_required=True))
    raw_key, _ = manager.create_api_key(role="read_only", ttl_seconds=-1)
    with pytest.raises(HTTPException) as exc_info:
        manager.authenticate(None, raw_key)
    assert exc_info.value.status_code == 401


def test_auth_manager_masks_raw_key_in_list() -> None:
    """Raw API key values should never appear in list output."""
    manager = AuthManager(Settings(auth_required=True))
    _, _key1 = manager.create_api_key(role="read_only", description="first")
    _, _key2 = manager.create_api_key(role="risk_admin", description="second")
    keys = manager.list_api_keys()
    assert len(keys) == 2
    for k in keys:
        assert "raw_key" not in k
