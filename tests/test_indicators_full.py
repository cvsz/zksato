from datetime import UTC, datetime, timedelta

import pytest

from zksato.domain import Candle
from zksato.indicators import (
    adx,
    atr,
    bollinger_bands,
    ema,
    ema_series,
    highest,
    lowest,
    max_drawdown_pct,
    rsi,
    sma,
    vwap,
)


def candles(count: int, *, volume: float = 100.0) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    result = []
    for index in range(count):
        close = 100.0 + index
        result.append(
            Candle(
                timestamp=start + timedelta(minutes=index),
                open=close - 0.25,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=volume,
            )
        )
    return result


def test_moving_average_and_extreme_indicator_edges() -> None:
    assert sma([1.0, 2.0], 0) is None
    assert sma([1.0, 2.0], 3) is None
    assert sma([1.0, 2.0, 3.0], 2) == pytest.approx(2.5)

    assert ema_series([], 2) == []
    assert ema_series([1.0], 0) == []
    series = ema_series([1.0, 2.0, 3.0], 2)
    assert len(series) == 3
    assert series[-1] > series[0]
    assert ema([1.0], 2) is None
    assert ema([1.0, 2.0, 3.0], 2) == pytest.approx(series[-1])

    assert highest([1.0], 0) is None
    assert highest([1.0], 2) is None
    assert highest([1.0, 4.0, 2.0], 2) == 4.0
    assert lowest([1.0], 0) is None
    assert lowest([1.0], 2) is None
    assert lowest([1.0, 4.0, 2.0], 2) == 2.0


def test_rsi_covers_insufficient_rising_and_mixed_series() -> None:
    assert rsi([1.0, 2.0], 2) is None
    assert rsi([1.0, 2.0, 3.0], 2) == 100.0
    value = rsi([10.0, 11.0, 10.0, 11.0, 10.0], 4)
    assert value == pytest.approx(50.0)


def test_atr_bollinger_and_vwap_edges() -> None:
    sample = candles(6)
    assert atr(sample[:2], 2) is None
    assert atr(sample, 2) is not None

    assert bollinger_bands([1.0], 1) is None
    assert bollinger_bands([1.0, 2.0], 3) is None
    lower, middle, upper = bollinger_bands([1.0, 2.0, 3.0, 4.0], 4) or (0.0, 0.0, 0.0)
    assert lower < middle < upper
    assert middle == pytest.approx(2.5)

    assert vwap([]) is None
    assert vwap(candles(3, volume=0.0)) is None
    full = vwap(sample)
    recent = vwap(sample, period=2)
    assert full is not None
    assert recent is not None
    assert recent > full


def test_adx_and_max_drawdown_edges() -> None:
    assert adx(candles(3), 2) is None
    trending = candles(8)
    value = adx(trending, 2)
    assert value is not None
    assert 0.0 <= value <= 100.0

    flat_start = datetime(2026, 1, 1, tzinfo=UTC)
    flat = [
        Candle(
            timestamp=flat_start + timedelta(minutes=index),
            open=100,
            high=100,
            low=100,
            close=100,
            volume=100,
        )
        for index in range(8)
    ]
    assert adx(flat, 2) == 0.0

    assert max_drawdown_pct([]) == 0.0
    assert max_drawdown_pct([100.0, 120.0, 90.0, 135.0]) == pytest.approx(25.0)
