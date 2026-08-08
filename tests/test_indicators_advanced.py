from datetime import UTC, datetime, timedelta

from zksato.domain import Candle
from zksato.indicators import adx, atr, bollinger_bands, vwap


def candles(count: int = 40) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            timestamp=start + timedelta(minutes=index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100.5 + index,
            volume=1000 + index,
        )
        for index in range(count)
    ]


def test_advanced_indicators_return_values() -> None:
    rows = candles()
    assert atr(rows, 14) is not None
    assert adx(rows, 14) is not None
    assert vwap(rows, 20) is not None
    bands = bollinger_bands([item.close for item in rows], 20)
    assert bands is not None
    assert bands[0] < bands[1] < bands[2]
