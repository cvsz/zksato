"""Technical indicators for zksato strategies."""

from __future__ import annotations

from typing import Any

import numpy as np


def rsi(prices: list[float], period: int = 14) -> list[float]:
    """Relative Strength Index."""
    if len(prices) < period + 1:
        return []

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        return [100.0] * (len(prices) - period)

    rs = avg_gain / avg_loss
    rsi_values = [100 - (100 / (1 + rs))]

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

    return rsi_values


def ema(prices: list[float], period: int) -> float:
    """Exponential Moving Average - returns last value."""
    if len(prices) < period:
        return prices[-1] if prices else 0.0

    multiplier = 2 / (period + 1)
    ema_value = sum(prices[:period]) / period

    for price in prices[period:]:
        ema_value = (price - ema_value) * multiplier + ema_value

    return ema_value


def ema_series(prices: list[float], period: int) -> list[float]:
    """Exponential Moving Average - returns full series."""
    if len(prices) < period:
        return []

    multiplier = 2 / (period + 1)
    ema_values = []
    ema_value = sum(prices[:period]) / period
    ema_values.append(ema_value)

    for price in prices[period:]:
        ema_value = (price - ema_value) * multiplier + ema_value
        ema_values.append(ema_value)

    return ema_values


def sma_series(prices: list[float], period: int) -> list[float]:
    """Simple Moving Average series."""
    if len(prices) < period:
        return []

    sma_values = [
        sum(prices[i - period + 1 : i + 1]) / period for i in range(period - 1, len(prices))
    ]

    return sma_values


def macd_series(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[float], list[float], list[float]]:
    """MACD: returns (macd_line, signal_line, histogram)."""
    fast_ema = ema_series(prices, fast)
    slow_ema = ema_series(prices, slow)

    if not fast_ema or not slow_ema:
        return [], [], []

    # Align lengths
    min_len = min(len(fast_ema), len(slow_ema))
    fast_ema = fast_ema[-min_len:]
    slow_ema = slow_ema[-min_len:]

    macd_line = [f - s for f, s in zip(fast_ema, slow_ema, strict=False)]
    signal_line = ema_series(macd_line, signal)

    if not signal_line:
        return macd_line, [], []

    # Align signal with macd
    min_len2 = min(len(macd_line), len(signal_line))
    macd_line = macd_line[-min_len2:]
    signal_line = signal_line[-min_len2:]

    histogram = [m - s for m, s in zip(macd_line, signal_line, strict=False)]

    return macd_line, signal_line, histogram


def bollinger_bands(
    prices: list[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[list[float], list[float], list[float]]:
    """Bollinger Bands: returns (upper, middle, lower)."""
    if len(prices) < period:
        return [], [], []

    sma = sma_series(prices, period)
    upper = []
    lower = []

    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1 : i + 1]
        std = np.std(window)
        middle = sma[i - period + 1]
        upper.append(middle + std_dev * std)
        lower.append(middle - std_dev * std)

    return upper, sma, lower


def bollinger_bands_series(
    prices: list[float],
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[list[float], list[float], list[float]]:
    """Alias for bollinger_bands."""
    return bollinger_bands(prices, period, std_dev)


def atr(candles: list[Any], period: int = 14) -> list[float]:
    """Average True Range from candles."""
    if len(candles) < period + 1:
        return []

    true_ranges = []
    for i in range(1, len(candles)):
        high = getattr(candles[i], "high", getattr(candles[i], "h", 0))
        low = getattr(candles[i], "low", getattr(candles[i], "l", 0))
        prev_close = getattr(candles[i - 1], "close", getattr(candles[i - 1], "c", 0))

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return []

    atr_values = [sum(true_ranges[:period]) / period]

    for i in range(period, len(true_ranges)):
        atr_values.append((atr_values[-1] * (period - 1) + true_ranges[i]) / period)

    return atr_values


def stochastic_oscillator(
    candles: list[Any],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[list[float], list[float]]:
    """Stochastic Oscillator: returns (%K, %D)."""
    if len(candles) < k_period:
        return [], []

    k_values = []
    for i in range(k_period - 1, len(candles)):
        window = candles[i - k_period + 1 : i + 1]
        highs = [getattr(c, "high", getattr(c, "h", 0)) for c in window]
        lows = [getattr(c, "low", getattr(c, "l", 0)) for c in window]
        close = getattr(candles[i], "close", getattr(candles[i], "c", 0))

        highest_high = max(highs)
        lowest_low = min(lows)

        if highest_high == lowest_low:
            k_values.append(50.0)
        else:
            k_values.append(100 * (close - lowest_low) / (highest_high - lowest_low))

    if len(k_values) < d_period:
        return k_values, []

    d_values = [
        sum(k_values[i - d_period + 1 : i + 1]) / d_period
        for i in range(d_period - 1, len(k_values))
    ]

    return k_values, d_values


def williams_r(candles: list[Any], period: int = 14) -> list[float]:
    """Williams %R."""
    if len(candles) < period:
        return []

    wr_values = []
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1 : i + 1]
        highs = [getattr(c, "high", getattr(c, "h", 0)) for c in window]
        lows = [getattr(c, "low", getattr(c, "l", 0)) for c in window]
        close = getattr(candles[i], "close", getattr(candles[i], "c", 0))

        highest_high = max(highs)
        lowest_low = min(lows)

        if highest_high == lowest_low:
            wr_values.append(-50.0)
        else:
            wr_values.append(-100 * (highest_high - close) / (highest_high - lowest_low))

    return wr_values


def vwap(candles: list[Any]) -> list[float]:
    """Volume Weighted Average Price."""
    if not candles:
        return []

    vwap_values = []
    cum_volume = 0.0
    cum_pv = 0.0

    for candle in candles:
        high = getattr(candle, "high", getattr(candle, "h", 0))
        low = getattr(candle, "low", getattr(candle, "l", 0))
        close = getattr(candle, "close", getattr(candle, "c", 0))
        volume = getattr(candle, "volume", getattr(candle, "v", 0))

        typical_price = (high + low + close) / 3
        cum_pv += typical_price * volume
        cum_volume += volume

        if cum_volume > 0:
            vwap_values.append(cum_pv / cum_volume)
        else:
            vwap_values.append(typical_price)

    return vwap_values


def rate_of_change(prices: list[float], period: int) -> list[float]:
    """Rate of Change."""
    if len(prices) < period + 1:
        return []

    roc_values = [
        (prices[i] - prices[i - period]) / prices[i - period] for i in range(period, len(prices))
    ]

    return roc_values


def highest(prices: list[float]) -> float:
    """Highest value in list."""
    return max(prices) if prices else 0.0
