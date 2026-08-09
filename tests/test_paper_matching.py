import pytest

from zksato.broker.paper import PaperBroker
from zksato.domain import OrderIntent, OrderStatus, Quote, Side
from zksato.store import StateStore


@pytest.mark.asyncio
async def test_resting_buy_limit_matches_on_later_quote_with_price_improvement() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="AOT", last=40.0, bid=39.5, offer=40.5))
    broker = PaperBroker(store, initial_cash=100_000.0, price_improvement=True)
    order = await broker.place_order(
        OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=39.0,
            client_order_id="resting-buy",
        )
    )
    assert order.status == OrderStatus.ACCEPTED

    matched = await broker.process_quote(Quote(symbol="AOT", last=38.8, bid=38.7, offer=38.9))
    assert len(matched) == 1
    assert matched[0].status == OrderStatus.FILLED
    assert matched[0].average_fill_price == pytest.approx(38.9)
    assert sum(fill.quantity for fill in store.list_fills()) == 100


@pytest.mark.asyncio
async def test_resting_limit_can_partial_fill_over_multiple_quotes() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="PTT", last=30.0, bid=29.5, offer=30.5))
    broker = PaperBroker(
        store,
        initial_cash=100_000.0,
        max_fill_quantity_per_quote=40,
    )
    order = await broker.place_order(
        OrderIntent(
            symbol="PTT",
            side=Side.BUY,
            quantity=100,
            price=30.0,
            client_order_id="partial-limit",
        )
    )
    assert order.status == OrderStatus.ACCEPTED

    quote = Quote(symbol="PTT", last=29.8, bid=29.7, offer=29.9)
    first = (await broker.process_quote(quote))[0]
    assert first.status == OrderStatus.PARTIALLY_FILLED
    assert first.filled_quantity == 40
    second = (await broker.process_quote(quote.model_copy(update={"last": 29.7, "offer": 29.8})))[0]
    assert second.status == OrderStatus.PARTIALLY_FILLED
    assert second.filled_quantity == 80
    third = (await broker.process_quote(quote.model_copy(update={"last": 29.6, "offer": 29.7})))[0]
    assert third.status == OrderStatus.FILLED
    assert third.filled_quantity == 100
    fills = list(reversed(store.list_fills()))
    assert [item.quantity for item in fills] == [40, 40, 20]


@pytest.mark.asyncio
async def test_partial_fill_remainder_can_be_cancelled() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="CPALL", last=70.0, bid=69.5, offer=70.5))
    broker = PaperBroker(store, initial_cash=100_000.0, max_fill_quantity_per_quote=25)
    order = await broker.place_order(
        OrderIntent(symbol="CPALL", side=Side.BUY, quantity=100, price=69.0)
    )
    await broker.process_quote(Quote(symbol="CPALL", last=68.8, bid=68.7, offer=68.9))
    assert order.status == OrderStatus.PARTIALLY_FILLED
    cancelled = await broker.cancel_order(str(order.id))
    assert cancelled.status == OrderStatus.CANCELLED
    assert cancelled.filled_quantity == 25


@pytest.mark.asyncio
async def test_restart_restores_client_id_and_open_limit_matching() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="KBANK", last=150.0, bid=149.5, offer=150.5))
    first = PaperBroker(store, initial_cash=100_000.0)
    intent = OrderIntent(
        symbol="KBANK",
        side=Side.BUY,
        quantity=10,
        price=149.0,
        client_order_id="restart-safe",
    )
    order = await first.place_order(intent)
    assert order.status == OrderStatus.ACCEPTED

    restarted = PaperBroker(store, initial_cash=100_000.0)
    with pytest.raises(ValueError, match="duplicate client_order_id"):
        await restarted.place_order(intent)
    matched = await restarted.process_quote(
        Quote(symbol="KBANK", last=148.8, bid=148.7, offer=148.9)
    )
    assert matched[0].id == order.id
    assert matched[0].status == OrderStatus.FILLED
