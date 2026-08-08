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
