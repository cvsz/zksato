from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

import pytest

from zksato.broker.paper import PaperBroker
from zksato.domain import (
    FillRecord,
    OrderIntent,
    OrderStatus,
    OrderType,
    PortfolioSnapshot,
    Position,
    Quote,
    Side,
)
from zksato.store import StateStore


def round_currency(value: float | Decimal) -> Decimal:
    """Rounds currency to 2 decimal places using standard financial round-half-up."""
    d = Decimal(str(value)) if not isinstance(value, Decimal) else value
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def test_order_intent_strictly_rejects_non_positive_prices_and_quantities() -> None:
    # Negative quantity
    with pytest.raises(ValueError):
        OrderIntent(
            symbol="PTT",
            side=Side.BUY,
            quantity=-100,
            price=35.0,
            order_type=OrderType.LIMIT,
        )

    # Zero quantity
    with pytest.raises(ValueError):
        OrderIntent(
            symbol="PTT",
            side=Side.BUY,
            quantity=0,
            price=35.0,
            order_type=OrderType.LIMIT,
        )

    # Negative price
    with pytest.raises(ValueError):
        OrderIntent(
            symbol="PTT",
            side=Side.BUY,
            quantity=100,
            price=-35.0,
            order_type=OrderType.LIMIT,
        )

    # Zero price for limit order
    with pytest.raises(ValueError):
        OrderIntent(
            symbol="PTT",
            side=Side.BUY,
            quantity=100,
            price=0.0,
            order_type=OrderType.LIMIT,
        )


def test_fill_record_rejects_non_positive_values_and_negative_fees() -> None:
    # Quantity <= 0
    with pytest.raises(ValueError):
        FillRecord(symbol="PTT", side=Side.BUY, quantity=0, price=35.0)

    # Price <= 0
    with pytest.raises(ValueError):
        FillRecord(symbol="PTT", side=Side.BUY, quantity=100, price=0.0)

    # Negative fee
    with pytest.raises(ValueError):
        FillRecord(symbol="PTT", side=Side.BUY, quantity=100, price=35.0, fee=-1.0)


def test_position_pnl_long_and_short_invariants() -> None:
    # Long position
    pos_long = Position(
        symbol="PTT",
        quantity=1000.0,
        average_price=35.0,
        market_price=38.5,
        market_value=38500.0,
        cost_value=35000.0,
        unrealized_pnl=3500.0,
        unrealized_pnl_pct=10.0,
    )
    assert pos_long.unrealized_pnl == pos_long.market_value - pos_long.cost_value
    expected_pct = ((pos_long.market_price - pos_long.average_price) / pos_long.average_price) * 100
    assert math.isclose(pos_long.unrealized_pnl_pct, expected_pct, rel_tol=1e-5)

    # Short position (TFEX contract)
    pos_short = Position(
        symbol="S50M26",
        quantity=-10.0,
        average_price=950.0,
        market_price=940.0,
        market_value=-9400.0,
        cost_value=-9500.0,
        unrealized_pnl=100.0,
        unrealized_pnl_pct=1.0526,
    )
    # Price dropped by 10 points on short: profit = (entry - exit) * abs(qty)
    pnl_short = (pos_short.average_price - pos_short.market_price) * abs(pos_short.quantity)
    assert pnl_short == 100.0


@pytest.mark.asyncio
async def test_cash_conservation_in_paper_matching() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="PTT", last=35.0, bid=34.75, offer=35.0))
    initial_cash = 100_000.0
    broker = PaperBroker(store, initial_cash=initial_cash, match_resting_limits=True)

    # Buy 100 shares of PTT at 35.0 THB (Cost = 3,500 THB)
    order = await broker.place_order(
        OrderIntent(
            symbol="PTT",
            side=Side.BUY,
            quantity=100,
            price=35.0,
            client_order_id="test-buy-001",
        )
    )
    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 100.0
    assert order.average_fill_price == 35.0

    fills = store.list_fills()
    assert len(fills) == 1
    assert fills[0].quantity == 100.0

    portfolio = await broker.portfolio()
    pos = next((p for p in portfolio.positions if p.symbol == "PTT"), None)
    assert pos is not None
    assert pos.quantity == 100.0

    # Total equity = Cash + Market Value
    total_equity = portfolio.cash + pos.market_value
    assert total_equity <= initial_cash  # Equity is conserved minus any commission/fees


def test_portfolio_snapshot_aggregation_invariants() -> None:
    positions = [
        Position(
            symbol="PTT",
            quantity=1000.0,
            average_price=35.0,
            market_price=36.0,
            market_value=36000.0,
            cost_value=35000.0,
            unrealized_pnl=1000.0,
            unrealized_pnl_pct=2.857,
        ),
        Position(
            symbol="AOT",
            quantity=500.0,
            average_price=60.0,
            market_price=58.0,
            market_value=29000.0,
            cost_value=30000.0,
            unrealized_pnl=-1000.0,
            unrealized_pnl_pct=-3.333,
        ),
    ]

    total_market_value = sum(p.market_value for p in positions)
    total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
    cash = 100_000.0

    snapshot = PortfolioSnapshot(
        cash=cash,
        market_value=total_market_value,
        equity=cash + total_market_value,
        realized_pnl=0.0,
        unrealized_pnl=total_unrealized_pnl,
        daily_pnl=total_unrealized_pnl,
        positions=positions,
    )

    assert snapshot.market_value == 65000.0
    assert snapshot.unrealized_pnl == 0.0
    assert snapshot.equity == 165000.0
    assert len(snapshot.positions) == 2
