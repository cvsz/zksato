"""
Test agent trading functionality - agent registration, authentication, heartbeat,
points/rewards, and point exchange.

These tests cover the zksato Agent OS sub-account system.
"""

from __future__ import annotations

import datetime as dt

from zksato.agent_trading.models import (
    AgentLoginRequest,
    AgentRegisterRequest,
)
from zksato.agent_trading.service import AgentService
from zksato.domain import Candle
from zksato.hyperopt import HyperoptEngine, run_hyperopt
from zksato.store import StateStore
from zksato.strategy_freqtrade import strategy_registry


def test_agent_registration_and_login():
    """Test agent registration and login flow."""
    store = StateStore()
    service = AgentService(store)

    # Register agent
    result = service.register_agent(
        AgentRegisterRequest(
            name="test_agent",
            email="test@example.com",
            password="secure_password123",
            wallet_address="0x1234abcdef",
            initial_balance=50000.0,
        )
    )
    assert result["agent_id"] is not None
    assert result["name"] == "test_agent"
    assert result["identity_status"] == "normal"
    assert result["is_verified"] is False

    # Verify store state
    agent = store.get_agent_by_id(result["agent_id"])
    assert agent is not None
    assert agent["name"] == "test_agent"
    assert agent["cash"] == 50000.0


def test_login_with_wrong_password():
    """Test login with wrong password raises ValueError."""
    store = StateStore()
    service = AgentService(store)

    service.register_agent(
        AgentRegisterRequest(
            name="test_agent",
            email="test@example.com",
            password="secure_password123",
            wallet_address="0x1234abcdef",
        )
    )

    try:
        service.login_agent(AgentLoginRequest(name="test_agent", password="wrong_password"))
        raise AssertionError("Expected ValueError for wrong password")
    except ValueError as exc:
        assert "Invalid credentials" in str(exc)


def test_heartbeat_returns_agent_status():
    """Test heartbeat returns agent status."""
    store = StateStore()
    service = AgentService(store)

    result = service.register_agent(
        AgentRegisterRequest(
            name="test_agent",
            email="test@example.com",
            password="secure_password123",
            wallet_address="0x1234abcdef",
        )
    )

    heartbeat = service.agent_heartbeat(str(result["agent_id"]))
    assert str(heartbeat.agent_id) == str(result["agent_id"])
    assert heartbeat.recommended_poll_interval_seconds == 30


def test_points_exchange_for_cash():
    """Test exchanging points for cash."""
    store = StateStore()
    service = AgentService(store)

    result = service.register_agent(
        AgentRegisterRequest(
            name="test_agent",
            email="test@example.com",
            password="secure_password123",
            wallet_address="0x1234abcdef",
        )
    )

    agent_id = result["agent_id"]

    # Add points manually via store
    store.add_agent_points(agent_id, 100, reason="test_reward")

    # Exchange 50 points for cash
    result = service.exchange_points_for_cash(agent_id, 50)
    assert result["success"] is True
    assert result["points_exchanged"] == 50
    assert result["cash_added"] == 50000.0
    assert result["remaining_points"] == 0


def test_exchange_insufficient_points():
    """Test exchanging more points than available."""
    store = StateStore()
    service = AgentService(store)

    result = service.register_agent(
        AgentRegisterRequest(
            name="test_agent",
            email="test@example.com",
            password="secure_password123",
            wallet_address="0x1234abcdef",
        )
    )

    agent_id = result["agent_id"]

    try:
        service.exchange_points_for_cash(agent_id, 999999)
        raise AssertionError("Expected ValueError for insufficient points")
    except ValueError as exc:
        assert "Insufficient points" in str(exc)


def test_hyperopt_engine_creation():
    """Test hyperopt engine creation."""
    candles = [
        Candle(
            timestamp=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
            symbol="AOT",
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        for _ in range(30)
    ]

    strategy_class = strategy_registry.get("ema_cross")
    engine = HyperoptEngine(
        strategy_class=strategy_class,
        symbol="AOT",
        candles=candles,
        loss_function_name="OnlyProfitHyperOptLoss",
        n_epochs=5,
    )
    assert engine.strategy_class is not None
    assert engine.symbol == "AOT"
    assert len(engine.candles) == 30
    assert engine.n_epochs == 5


def test_hyperopt_run():
    """Test running hyperopt optimization."""
    candles = [
        Candle(
            timestamp=dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
            symbol="AOT",
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        for _ in range(30)
    ]

    result = run_hyperopt(
        strategy_name="ema_cross",
        symbol="AOT",
        candles=candles,
        loss_function="OnlyProfitHyperOptLoss",
        n_epochs=5,
    )
    assert result.best_trial is not None
    assert result.n_epochs == 5
    assert result.loss_function == "OnlyProfitHyperOptLoss"
