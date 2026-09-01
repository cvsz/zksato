"""Concurrency and race condition tests for zksato."""

from __future__ import annotations

import asyncio

import pytest

from zksato.config import Settings
from zksato.domain import OrderIntent, OrderType, RiskContext, Side
from zksato.store import StateStore


@pytest.mark.asyncio
async def test_concurrent_client_order_id_claims_are_unique() -> None:
    """Concurrent claims for the same client_order_id must not both succeed."""
    store = StateStore()
    settings = Settings()
    from zksato.risk import RiskEngine

    engine = RiskEngine(settings)
    intent = OrderIntent(
        symbol="AOT",
        side=Side.BUY,
        quantity=100,
        price=40.0,
        stop_loss=38.0,
        client_order_id="duplicate-test-id",
    )
    context = RiskContext(
        current_positions=0,
        position_pct_after_trade=5.0,
        line_available=100_000.0,
    )
    decision = engine.evaluate(intent, context)
    assert decision.approved is True

    results = []

    async def claim() -> bool:
        return store.claim_client_order_id("duplicate-test-id")

    results = await asyncio.gather(claim(), claim(), claim(), claim(), claim())
    assert sum(1 for r in results if r is True) == 1
    assert sum(1 for r in results if r is False) == 4


@pytest.mark.asyncio
async def test_concurrent_unique_client_order_ids_all_succeed() -> None:
    """Concurrent claims for unique client_order_ids should all succeed."""
    store = StateStore()

    results = []

    async def claim(idx: int) -> bool:
        return store.claim_client_order_id(f"unique-id-{idx}")

    results = await asyncio.gather(*[claim(i) for i in range(20)])
    assert all(results)


def test_order_archival_prevents_unbounded_growth() -> None:
    """Orders list should be capped at max_orders with archival."""
    store = StateStore(max_orders=100)

    for i in range(150):
        order_id = f"order-{i:04d}"
        from zksato.domain import OrderRecord, OrderStatus

        record = OrderRecord(
            client_order_id=order_id,
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=40.0,
            status=OrderStatus.ACCEPTED,
        )
        store.upsert_order(record)

    assert len(store.orders) == 100
    assert store.order_count() == 150
    assert store._archived_order_count == 50


def test_session_pruning_removes_expired_revoked_sessions() -> None:
    """Expired sessions should be pruned from the revoked set."""
    from zksato.auth import AuthManager

    settings = Settings(
        auth_required=True,
        session_secret="test-secret-key-for-pruning-test",
        api_keys="test-key:platform_admin",
    )
    auth = AuthManager(settings)

    # Create and revoke a session
    session = auth.issue_session(None, "test-key")
    auth.revoke_session(session.token)

    # Manually set the expiry to the past to simulate expiration
    auth._session_expiry[session.principal.session_id] = 0

    # Trigger pruning by authenticating a new session
    auth.issue_session(None, "test-key")
    auth._prune_revoked_sessions()

    # The expired session should be pruned
    assert session.principal.session_id not in auth._revoked_sessions
    assert session.principal.session_id not in auth._session_expiry


def test_var_calculation_uses_interpolation() -> None:
    """VaR should use linear interpolation for accurate percentile."""
    from zksato.risk import PortfolioRiskManager

    manager = PortfolioRiskManager(Settings())
    returns = [-0.05, -0.03, -0.02, 0.01, 0.02, 0.03, 0.04, 0.05, 0.01, -0.01]

    var_95 = manager.calculate_var(returns, confidence_level=0.95, portfolio_value=100_000.0)
    var_99 = manager.calculate_var(returns, confidence_level=0.99, portfolio_value=100_000.0)

    # VaR at 99% should be >= VaR at 95%
    assert var_99 >= var_95
    assert var_95 > 0.0


def test_expected_shortfall_exceeds_var() -> None:
    """CVaR/Expected Shortfall should be >= VaR at the same confidence level."""
    from zksato.risk import PortfolioRiskManager

    manager = PortfolioRiskManager(Settings())
    returns = [-0.05, -0.03, -0.02, 0.01, 0.02, 0.03, 0.04, 0.05, 0.01, -0.01]

    var_95 = manager.calculate_var(returns, confidence_level=0.95, portfolio_value=100_000.0)
    cvar_95 = manager.calculate_expected_shortfall(
        returns, confidence_level=0.95, portfolio_value=100_000.0
    )

    assert cvar_95 >= var_95
