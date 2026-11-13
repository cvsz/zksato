"""Test assertions for zksato."""

from __future__ import annotations

from typing import Any

from zksato_core.models import OrderRecord, OrderStatus, RiskDecision


def assert_order_filled(order: OrderRecord, expected_quantity: float | None = None) -> None:
    """Assert that an order is filled."""
    assert order.status == OrderStatus.FILLED, f"Expected FILLED, got {order.status}"
    if expected_quantity is not None:
        assert order.filled_quantity == expected_quantity, (
            f"Expected quantity {expected_quantity}, got {order.filled_quantity}"
        )


def assert_order_rejected(order: OrderRecord, reason_contains: str | None = None) -> None:
    """Assert that an order is rejected."""
    assert order.status == OrderStatus.REJECTED, f"Expected REJECTED, got {order.status}"
    if reason_contains and order.message:
        assert reason_contains in order.message, (
            f"Expected rejection reason to contain '{reason_contains}', got '{order.message}'"
        )


def assert_risk_rejected(result: RiskDecision, reason_contains: str | None = None) -> None:
    """Assert that risk check rejected an order."""
    assert not result.allowed, "Expected risk check to reject"
    if reason_contains and result.reason:
        assert reason_contains in result.reason, (
            f"Expected rejection reason to contain '{reason_contains}', got '{result.reason}'"
        )


def assert_risk_allowed(result: RiskDecision) -> None:
    """Assert that risk check allowed an order."""
    assert result.allowed, f"Expected risk check to allow, got rejection: {result.reason}"


def assert_portfolio_balanced(
    local_portfolio: Any,
    broker_portfolio: Any,
    tolerance_pct: float = 0.01,
) -> None:
    """Assert that local and broker portfolios match within tolerance."""
    cash_diff = abs(local_portfolio.cash - broker_portfolio.cash)
    cash_tolerance = max(local_portfolio.cash, broker_portfolio.cash) * tolerance_pct
    assert cash_diff <= cash_tolerance, (
        f"Cash mismatch: local={local_portfolio.cash}, broker={broker_portfolio.cash}, diff={cash_diff}"
    )

    equity_diff = abs(local_portfolio.equity - broker_portfolio.equity)
    equity_tolerance = max(local_portfolio.equity, broker_portfolio.equity) * tolerance_pct
    assert equity_diff <= equity_tolerance, (
        f"Equity mismatch: local={local_portfolio.equity}, broker={broker_portfolio.equity}, diff={equity_diff}"
    )
