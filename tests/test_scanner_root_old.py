from zksato.domain import Quote
from zksato.scanner import MarketScanner


def test_scanner_ranks_momentum_and_volume() -> None:
    rows = MarketScanner().scan(
        [
            Quote(symbol="AOT", last=42, previous_close=40, volume=1_000_000),
            Quote(symbol="PTT", last=31, previous_close=31, volume=2_000_000),
        ]
    )
    assert rows[0].symbol == "AOT"
    assert rows[0].score > 0
