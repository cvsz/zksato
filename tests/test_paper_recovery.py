from zksato.domain import Side
from zksato.persistence import SqlStateStore
from zksato.portfolio import PaperPortfolio


def test_paper_portfolio_survives_store_restart(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'paper.db'}"
    store = SqlStateStore(database_url)
    portfolio = PaperPortfolio(store, initial_cash=100_000)
    portfolio.apply_fill("AOT", Side.BUY, 100, 40)
    store.close()

    recovered_store = SqlStateStore(database_url)
    recovered = PaperPortfolio(recovered_store, initial_cash=999_999)
    snapshot = recovered.snapshot()
    assert snapshot.cash == 96_000
    assert len(snapshot.positions) == 1
    assert snapshot.positions[0].symbol == "AOT"
    assert snapshot.positions[0].quantity == 100
    assert snapshot.positions[0].average_price == 40
    recovered_store.close()
