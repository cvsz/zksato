from datetime import UTC, datetime, timedelta

import pytest

from zksato.agent_os import (
    AgentExecutionEngine,
    AgentPermission,
    AgentSkillHub,
    AgentSubAccountManager,
)
from zksato.broker.paper import PaperBroker
from zksato.config import Settings
from zksato.domain import Quote
from zksato.service import TradingService
from zksato.store import StateStore


def test_agent_subaccount_isolation_and_permissions() -> None:
    manager = AgentSubAccountManager()
    acc = manager.create_subaccount("momentum_agent", collateral_usd=500.0)

    assert acc.agent_name == "momentum_agent"
    assert acc.current_cash_usd == 500.0
    assert acc.can_perform(AgentPermission.SUBMIT_INTENT) is True
    # Non-negotiable security invariant: agent sub-accounts can never withdraw funds
    assert acc.can_perform(AgentPermission.WITHDRAW) is False

    # Freeze subaccount
    assert manager.freeze_subaccount(acc.sub_account_id) is True
    assert acc.can_perform(AgentPermission.SUBMIT_INTENT) is False


@pytest.mark.asyncio
async def test_agent_skill_hub_execution() -> None:
    hub = AgentSkillHub()

    async def sample_calc(a: int, b: int) -> dict[str, int]:
        return {"sum": a + b}

    hub.register(
        name="add_numbers",
        description="Adds two integers together",
        parameters_schema={"a": {"type": "integer"}, "b": {"type": "integer"}},
        handler=sample_calc,
    )

    res = await hub.execute_skill("add_numbers", a=5, b=10)
    assert res["success"] is True
    assert res["result"]["sum"] == 15

    # Non-existent skill
    missing = await hub.execute_skill("unknown_skill")
    assert missing["success"] is False
    assert "not found" in missing["error"]


@pytest.mark.asyncio
async def test_agent_execution_engine_routing() -> None:
    settings = Settings(trading_mode="paper")
    store = StateStore()
    store.update_quote(
        Quote(
            symbol="BTC/USDT",
            bid=50000.0,
            offer=50010.0,
            last=50005.0,
            timestamp=datetime.now(UTC),
        )
    )
    broker = PaperBroker(store)
    service = TradingService(settings, broker, store)

    subaccount_mgr = AgentSubAccountManager()
    acc = subaccount_mgr.create_subaccount("grid_bot", collateral_usd=2000.0)

    engine = AgentExecutionEngine(settings, service, subaccount_mgr)

    # 1. Test get_market_quote skill
    quote_res = await engine.skills.execute_skill("get_market_quote", symbol="BTC/USDT")
    assert quote_res["success"] is True
    assert quote_res["result"]["found"] is True
    assert quote_res["result"]["last"] == 50005.0

    # 2. Test submit_guarded_order skill
    order_res = await engine.skills.execute_skill(
        "submit_guarded_order",
        sub_account_id=acc.sub_account_id,
        symbol="BTC/USDT",
        side="buy",
        quantity=1,
        price=50000.0,
        order_type="limit",
    )
    assert order_res["success"] is True
    assert order_res["result"]["approved"] is True
    order_id = order_res["result"]["order_id"]
    assert order_id is not None

    # 3. Test get_account_summary skill
    acc_summary = await engine.skills.execute_skill(
        "get_account_summary", sub_account_id=acc.sub_account_id
    )
    assert acc_summary["success"] is True
    assert acc_summary["result"]["sub_account_id"] == acc.sub_account_id
    assert acc_summary["result"]["allocated_collateral_usd"] == 2000.0

    # 4. Test cancel_agent_order skill
    cancel_res = await engine.skills.execute_skill(
        "cancel_agent_order",
        sub_account_id=acc.sub_account_id,
        order_id=order_id,
    )
    assert cancel_res["success"] is True


@pytest.mark.asyncio
async def test_agent_guarded_order_stale_market_data_rejected() -> None:
    """Agent orders must be rejected when market data is stale (fail closed)."""
    settings = Settings(trading_mode="paper", market_data_stale_seconds=10.0)
    store = StateStore()
    store.update_quote(
        Quote(
            symbol="BTC/USDT",
            bid=50000.0,
            offer=50010.0,
            last=50005.0,
            timestamp=datetime.now(UTC),
        )
    )
    # Age the quote directly in the store to exceed the staleness threshold
    quote = store.get_quote("BTC/USDT")
    assert quote is not None
    quote.timestamp = datetime.now(UTC) - timedelta(minutes=5)  # 5 minutes old >> 10s threshold

    broker = PaperBroker(store)
    service = TradingService(settings, broker, store)

    subaccount_mgr = AgentSubAccountManager()
    acc = subaccount_mgr.create_subaccount("grid_bot", collateral_usd=2000.0)

    engine = AgentExecutionEngine(settings, service, subaccount_mgr)

    order_res = await engine.skills.execute_skill(
        "submit_guarded_order",
        sub_account_id=acc.sub_account_id,
        symbol="BTC/USDT",
        side="buy",
        quantity=1,
        price=50000.0,
        order_type="limit",
    )
    assert order_res["success"] is True
    result = order_res["result"]
    assert result["approved"] is False
    assert any("stale" in r.lower() for r in result.get("reasons", []))


@pytest.mark.asyncio
async def test_agent_guarded_order_permission_denied() -> None:
    """Frozen sub-accounts must not be able to submit orders."""
    settings = Settings(trading_mode="paper")
    store = StateStore()
    store.update_quote(
        Quote(
            symbol="BTC/USDT",
            bid=50000.0,
            offer=50010.0,
            last=50005.0,
            timestamp=datetime.now(UTC),
        )
    )
    broker = PaperBroker(store)
    service = TradingService(settings, broker, store)

    subaccount_mgr = AgentSubAccountManager()
    acc = subaccount_mgr.create_subaccount("frozen_agent", collateral_usd=2000.0)
    subaccount_mgr.freeze_subaccount(acc.sub_account_id)

    engine = AgentExecutionEngine(settings, service, subaccount_mgr)

    order_res = await engine.skills.execute_skill(
        "submit_guarded_order",
        sub_account_id=acc.sub_account_id,
        symbol="BTC/USDT",
        side="buy",
        quantity=1,
        price=50000.0,
        order_type="limit",
    )
    assert order_res["success"] is True
    result = order_res["result"]
    assert result["approved"] is False
    assert "unauthorized" in result.get("reason", "").lower()


@pytest.mark.asyncio
async def test_agent_guarded_order_invalid_side_rejected() -> None:
    """Invalid side values must be rejected before reaching RiskEngine."""
    settings = Settings(trading_mode="paper")
    store = StateStore()
    broker = PaperBroker(store)
    service = TradingService(settings, broker, store)

    subaccount_mgr = AgentSubAccountManager()
    acc = subaccount_mgr.create_subaccount("bad_agent", collateral_usd=2000.0)

    engine = AgentExecutionEngine(settings, service, subaccount_mgr)

    order_res = await engine.skills.execute_skill(
        "submit_guarded_order",
        sub_account_id=acc.sub_account_id,
        symbol="BTC/USDT",
        side="invalid_side",
        quantity=1,
        price=50000.0,
        order_type="limit",
    )
    assert order_res["success"] is True
    result = order_res["result"]
    assert result["approved"] is False
    assert "side" in result.get("reason", "").lower()


@pytest.mark.asyncio
async def test_agent_guarded_order_zero_quantity_rejected() -> None:
    """Zero or negative quantity must be rejected before reaching RiskEngine."""
    settings = Settings(trading_mode="paper")
    store = StateStore()
    broker = PaperBroker(store)
    service = TradingService(settings, broker, store)

    subaccount_mgr = AgentSubAccountManager()
    acc = subaccount_mgr.create_subaccount("zero_qty_agent", collateral_usd=2000.0)

    engine = AgentExecutionEngine(settings, service, subaccount_mgr)

    order_res = await engine.skills.execute_skill(
        "submit_guarded_order",
        sub_account_id=acc.sub_account_id,
        symbol="BTC/USDT",
        side="buy",
        quantity=0,
        price=50000.0,
        order_type="limit",
    )
    assert order_res["success"] is True
    result = order_res["result"]
    assert result["approved"] is False
    assert "quantity" in result.get("reason", "").lower()
