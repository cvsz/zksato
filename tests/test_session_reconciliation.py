from zksato.broker.paper import PaperBroker
from zksato.domain import FillRecord, Quote, Side
from zksato.session_reconcile import SessionReconciliationService
from zksato.store import StateStore


async def test_session_reconciliation_matches_durable_fills_to_broker_portfolio() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="AOT", last=40, bid=39.75, offer=40.25))
    broker = PaperBroker(store, initial_cash=100_000)
    broker.account.apply_fill("AOT", Side.BUY, 100, 40)
    store.add_fill(
        FillRecord(
            broker_fill_id="paper-fill-1",
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40,
        )
    )
    report = await SessionReconciliationService(broker, store).run()
    assert report.matched is True
    assert report.expected_positions == {"AOT": 100}
    assert report.broker_positions == {"AOT": 100}


async def test_session_reconciliation_detects_position_discrepancy() -> None:
    store = StateStore()
    store.update_quote(Quote(symbol="PTT", last=30, bid=29.75, offer=30.25))
    broker = PaperBroker(store, initial_cash=100_000)
    # Broker has 100 PTT but local fills only record 50
    broker.account.apply_fill("PTT", Side.BUY, 100, 30)
    store.add_fill(
        FillRecord(
            broker_fill_id="paper-fill-ptty",
            symbol="PTT",
            side=Side.BUY,
            quantity=50,
            price=30,
        )
    )
    report = await SessionReconciliationService(broker, store).run()
    assert report.matched is False
    assert len(report.discrepancies) == 1
    disc = report.discrepancies[0]
    assert disc.symbol == "PTT"
    assert disc.expected_quantity == 50
    assert disc.broker_quantity == 100
    assert disc.difference == 50


async def test_session_reconciliation_empty_portfolio_matches() -> None:
    store = StateStore()
    broker = PaperBroker(store, initial_cash=100_000)
    report = await SessionReconciliationService(broker, store).run()
    assert report.matched is True
    assert report.discrepancies == []
    assert report.expected_positions == {}
    assert report.broker_positions == {}
