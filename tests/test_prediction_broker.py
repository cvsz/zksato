"""Dedicated tests for zksato.prediction.broker — PaperPredictionBroker.

Covers:
- Basic fill execution and state mutation.
- Settlement and P&L calculation.
- Risk rejections: invalid price, zero/excess order size, directional overexposure,
  market-exposure cap, and insufficient cash.
- Async create_order / cancel_order / fetch_open_orders / fetch_balance interface.
- Side normalisation in create_order.
- CPMM pool integration (slippage-gated fills).
"""
from __future__ import annotations

import pytest

from zksato.config import Settings
from zksato.domain import Side
from zksato.prediction.broker import Fill, PaperPredictionBroker, RiskRejected
from zksato.prediction.core import LiquidityPool, RiskLimits

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _broker(
    limits: RiskLimits | None = None,
    pool: LiquidityPool | None = None,
) -> PaperPredictionBroker:
    return PaperPredictionBroker(Settings(), limits=limits, pool=pool)


def _generous() -> RiskLimits:
    return RiskLimits(
        max_order_usd=5_000,
        max_market_exposure_usd=50_000,
        max_directional_shares=99_999,
    )


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


def test_execute_up_fill_updates_position_and_cash() -> None:
    broker = _broker(limits=_generous())
    fill = broker.execute(Side.UP, 0.55, 100.0)

    assert isinstance(fill, Fill)
    assert fill.side == Side.UP
    assert fill.shares > 0
    assert fill.price >= 0.55
    assert fill.total_cost > 0
    assert len(broker.fills) == 1
    assert broker.cash < broker.starting_cash
    assert broker.position.shares[Side.UP] > 0


def test_execute_down_fill_updates_down_position() -> None:
    broker = _broker(limits=_generous())
    broker.execute(Side.DOWN, 0.45, 50.0)
    assert broker.position.shares[Side.DOWN] > 0
    assert broker.position.shares[Side.UP] == 0.0


def test_multiple_fills_accumulate() -> None:
    broker = _broker(limits=_generous())
    broker.execute(Side.UP, 0.5, 10.0)
    broker.execute(Side.UP, 0.5, 10.0)
    assert len(broker.fills) == 2
    assert broker.position.shares[Side.UP] > 0


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------


def test_settle_up_winner_returns_pnl() -> None:
    broker = _broker(limits=_generous())
    broker.execute(Side.UP, 0.5, 100.0)
    pnl = broker.settle(Side.UP)
    assert isinstance(pnl, float)
    # With shares paid out as cash, pnl = cash - starting_cash
    assert broker.cash == broker.starting_cash + pnl


def test_settle_down_loser_gives_zero_payout() -> None:
    broker = _broker(limits=_generous())
    broker.execute(Side.UP, 0.5, 50.0)
    # Settling DOWN when we only hold UP shares → payout is 0
    pnl = broker.settle(Side.DOWN)
    assert pnl < 0  # lost the stake


# ---------------------------------------------------------------------------
# Risk rejections
# ---------------------------------------------------------------------------


def test_rejects_price_at_zero() -> None:
    with pytest.raises(RiskRejected, match="price must be between 0 and 1"):
        _broker().execute(Side.UP, 0.0, 5.0)


def test_rejects_price_at_one() -> None:
    with pytest.raises(RiskRejected, match="price must be between 0 and 1"):
        _broker().execute(Side.UP, 1.0, 5.0)


def test_rejects_price_above_one() -> None:
    with pytest.raises(RiskRejected, match="price must be between 0 and 1"):
        _broker().execute(Side.UP, 1.01, 5.0)


def test_rejects_zero_order_usd() -> None:
    with pytest.raises(RiskRejected, match="order exceeds configured order limit"):
        _broker().execute(Side.UP, 0.5, 0.0)


def test_rejects_negative_order_usd() -> None:
    with pytest.raises(RiskRejected, match="order exceeds configured order limit"):
        _broker().execute(Side.UP, 0.5, -1.0)


def test_rejects_order_exceeding_max() -> None:
    limits = RiskLimits(max_order_usd=5.0)
    with pytest.raises(RiskRejected, match="order exceeds configured order limit"):
        _broker(limits=limits).execute(Side.UP, 0.5, 10.0)


def test_rejects_insufficient_cash() -> None:
    limits = _generous()
    broker = _broker(limits=limits)
    broker.cash = 0.0
    with pytest.raises(RiskRejected, match="insufficient paper cash"):
        broker.execute(Side.UP, 0.5, 5.0)


def test_rejects_market_exposure_cap() -> None:
    limits = RiskLimits(
        max_order_usd=500, max_market_exposure_usd=30.0, max_directional_shares=99_999
    )
    broker = _broker(limits=limits)
    with pytest.raises(RiskRejected, match="market exposure limit reached"):
        broker.execute(Side.UP, 0.5, 50.0)


def test_rejects_directional_residual_exceeded() -> None:
    # max_directional_shares=3 → two fills of ~2 shares each would push residual to ~4
    limits = RiskLimits(
        max_order_usd=50, max_market_exposure_usd=50_000, max_directional_shares=3.0
    )
    broker = _broker(limits=limits)
    broker.execute(Side.UP, 0.5, 1.0)  # ~2 UP shares, residual 2 < 3, passes
    with pytest.raises(RiskRejected, match="directional residual limit reached"):
        broker.execute(Side.UP, 0.5, 1.0)  # would push residual to ~4 > 3


# ---------------------------------------------------------------------------
# Async API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_order_returns_filled_record() -> None:
    broker = _broker(limits=_generous())
    record = await broker.create_order("mkt-1", "up", 100.0, 0.55)
    assert record["status"] == "filled"
    assert record["market_id"] == "mkt-1"
    assert record["side"] == Side.UP.value


@pytest.mark.asyncio
async def test_create_order_normalises_uppercase_side() -> None:
    broker = _broker(limits=_generous())
    record = await broker.create_order("mkt-1", "UP", 10.0, 0.5)
    assert record["side"] == Side.UP.value


@pytest.mark.asyncio
async def test_create_order_rejects_invalid_side() -> None:
    broker = _broker(limits=_generous())
    with pytest.raises(ValueError, match="unsupported prediction side"):
        await broker.create_order("mkt-1", "long", 10.0, 0.5)


@pytest.mark.asyncio
async def test_cancel_order_returns_cancelled_status() -> None:
    broker = _broker(limits=_generous())
    record = await broker.create_order("mkt-1", "up", 10.0, 0.5)
    cancelled = await broker.cancel_order(record["id"])
    assert cancelled["status"] == "canceled"
    assert cancelled.get("id") == record["id"]


@pytest.mark.asyncio
async def test_cancel_order_raises_for_unknown_id() -> None:
    broker = _broker()
    with pytest.raises(ValueError, match="not found"):
        await broker.cancel_order("nonexistent-order-id")


@pytest.mark.asyncio
async def test_fetch_open_orders_returns_empty_initially() -> None:
    broker = _broker(limits=_generous())
    orders = await broker.fetch_open_orders("mkt-1")
    # Paper fills go straight to "filled" status — no open resting orders
    assert orders == []


@pytest.mark.asyncio
async def test_fetch_balance_returns_cash() -> None:
    broker = _broker(limits=_generous())
    balance = await broker.fetch_balance()
    assert "cash" in balance
    assert balance["cash"] == broker.cash


# ---------------------------------------------------------------------------
# CPMM pool integration
# ---------------------------------------------------------------------------


def test_pool_fill_uses_dynamic_price() -> None:
    pool = LiquidityPool(up_reserve=1000.0, down_reserve=1000.0)
    limits = RiskLimits(max_order_usd=500.0, max_slippage_bps=300.0)
    broker = _broker(limits=limits, pool=pool)

    fill = broker.execute(Side.UP, 0.50, 10.0)
    assert fill.price > 0.50  # CPMM price impact
    assert fill.shares > 0


def test_pool_rejects_high_slippage_order() -> None:
    pool = LiquidityPool(up_reserve=1000.0, down_reserve=1000.0)
    limits = RiskLimits(max_order_usd=5_000.0, max_slippage_bps=100.0)
    broker = _broker(limits=limits, pool=pool)

    with pytest.raises(RiskRejected, match="slippage .* exceeds limit"):
        broker.execute(Side.UP, 0.50, 800.0)
