import pytest

from zksato.broker.paper import PaperBroker
from zksato.domain import OrderIntent, OrderStatus, OrderType, Quote, Side
from zksato.store import StateStore


@pytest.mark.asyncio
async def test_market_orders_use_offer_and_bid_and_update_portfolio() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="AOT", last=40.0, bid=39.5, offer=40.5))
    broker = PaperBroker(store, initial_cash=100_000.0)

    buy = await broker.place_order(
        OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            client_order_id="market-buy",
        )
    )
    assert buy.status == OrderStatus.FILLED
    assert buy.average_fill_price == 40.5

    sell = await broker.place_order(
        OrderIntent(
            symbol="AOT",
            side=Side.SELL,
            quantity=40,
            order_type=OrderType.MARKET,
            client_order_id="market-sell",
        )
    )
    assert sell.status == OrderStatus.FILLED
    assert sell.average_fill_price == 39.5

    snapshot = await broker.portfolio()
    assert snapshot.positions[0].quantity == 60
    assert len(await broker.list_orders()) == 2


@pytest.mark.asyncio
async def test_market_order_without_quote_fails_closed() -> None:
    broker = PaperBroker(StateStore(), initial_cash=100_000.0)
    with pytest.raises(ValueError, match="current quote"):
        await broker.place_order(
            OrderIntent(
                symbol="PTT",
                side=Side.BUY,
                quantity=10,
                order_type=OrderType.MARKET,
            )
        )


@pytest.mark.asyncio
async def test_non_marketable_limits_are_accepted_and_cancellable() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="PTT", last=30.0, bid=29.5, offer=30.5))
    broker = PaperBroker(store, initial_cash=100_000.0)

    buy = await broker.place_order(
        OrderIntent(
            symbol="PTT",
            side=Side.BUY,
            quantity=100,
            price=29.0,
            client_order_id="limit-buy",
        )
    )
    assert buy.status == OrderStatus.ACCEPTED
    cancelled_buy = await broker.cancel_order(str(buy.id))
    assert cancelled_buy.status == OrderStatus.CANCELLED

    sell = await broker.place_order(
        OrderIntent(
            symbol="PTT",
            side=Side.SELL,
            quantity=10,
            price=31.0,
            client_order_id="limit-sell",
        )
    )
    assert sell.status == OrderStatus.ACCEPTED
    cancelled_sell = await broker.cancel_order(str(sell.id))
    assert cancelled_sell.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_rejects_filled_or_unknown_order() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="KBANK", last=150.0, bid=149.5, offer=150.5))
    broker = PaperBroker(store, initial_cash=100_000.0)
    filled = await broker.place_order(
        OrderIntent(symbol="KBANK", side=Side.BUY, quantity=10, price=151.0)
    )
    assert filled.status == OrderStatus.FILLED

    with pytest.raises(ValueError, match="only open"):
        await broker.cancel_order(str(filled.id))
    with pytest.raises(ValueError, match="not found"):
        await broker.cancel_order("missing-order")


@pytest.mark.asyncio
async def test_duplicate_id_on_accepted_limit_is_rejected() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="CPALL", last=70.0, bid=69.5, offer=70.5))
    broker = PaperBroker(store, initial_cash=100_000.0)
    intent = OrderIntent(
        symbol="CPALL",
        side=Side.BUY,
        quantity=10,
        price=69.0,
        client_order_id="accepted-duplicate",
    )
    first = await broker.place_order(intent)
    assert first.status == OrderStatus.ACCEPTED
    with pytest.raises(ValueError, match="duplicate client_order_id"):
        await broker.place_order(intent)
