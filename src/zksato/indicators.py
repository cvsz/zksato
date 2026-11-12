"""
High-performance technical indicators for zksato.

NumPy-vectorized indicator calculations for trading systems.
All functions are advisory/research only — no order execution.
"""

from __future__ import annotations

import math

import numpy as np

from zksato.domain import Candle


def _arr(values: list[float]) -> np.ndarray:
    if not values:
        return np.array([], dtype=np.float64)
    return np.asarray(values, dtype=np.float64)


def _ohlcv(candles: list[Candle]) -> tuple[np.ndarray, ...]:
    if not candles:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty, empty, empty
    return (
        np.array([c.open for c in candles], dtype=np.float64),
        np.array([c.high for c in candles], dtype=np.float64),
        np.array([c.low for c in candles], dtype=np.float64),
        np.array([c.close for c in candles], dtype=np.float64),
        np.array([c.volume for c in candles], dtype=np.float64),
    )


# ── Moving Averages ──────────────────────────────────────────────────────


def sma(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return float(np.mean(_arr(values)[-period:]))


def sma_series(values: list[float], period: int) -> list[float]:
    if period <= 0 or len(values) < period:
        return []
    arr = _arr(values)
    kernel = np.ones(period) / period
    result = np.convolve(arr, kernel, mode="valid")
    padded = np.full(len(arr), np.nan)
    padded[period - 1 :] = result
    return padded.tolist()


def ema_series(values: list[float], period: int) -> list[float]:
    if period <= 0 or not values:
        return []
    arr = _arr(values)
    alpha = 2.0 / (period + 1.0)
    result = np.empty(len(arr), dtype=np.float64)
    result[0] = arr[0]
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1.0 - alpha) * result[i - 1]
    return result.tolist()


def ema(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    series = ema_series(values, period)
    return series[-1] if series else None


def wma(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    arr = _arr(values)
    window = arr[-period:]
    weights = np.arange(1, period + 1, dtype=np.float64)
    return float(np.sum(window * weights) / weights.sum())


def wma_series(values: list[float], period: int) -> list[float]:
    if period <= 0 or len(values) < period:
        return []
    arr = _arr(values)
    weights = np.arange(1, period + 1, dtype=np.float64)
    kernel = weights / weights.sum()
    result = np.convolve(arr, kernel, mode="valid")
    padded = np.full(len(arr), np.nan)
    padded[period - 1 :] = result
    return padded.tolist()


# ── MACD ─────────────────────────────────────────────────────────────────


def macd(
    values: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[float, float, float] | None:
    if fast_period <= 0 or slow_period <= fast_period or signal_period <= 0:
        return None
    if len(values) < slow_period + signal_period:
        return None
    arr = _arr(values)
    fast_ema = np.array(ema_series(arr.tolist(), fast_period))
    slow_ema = np.array(ema_series(arr.tolist(), slow_period))
    macd_line = fast_ema - slow_ema
    if len(macd_line) < signal_period:
        return None
    signal_line = np.array(ema_series(macd_line.tolist(), signal_period))
    return float(macd_line[-1]), float(signal_line[-1]), float(macd_line[-1] - signal_line[-1])


def macd_series(
    values: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float], list[float], list[float]] | None:
    if fast_period <= 0 or slow_period <= fast_period or signal_period <= 0:
        return None
    if len(values) < slow_period + signal_period:
        return None
    arr = _arr(values)
    fast_ema = np.array(ema_series(arr.tolist(), fast_period))
    slow_ema = np.array(ema_series(arr.tolist(), slow_period))
    macd_line = fast_ema - slow_ema
    if len(macd_line) < signal_period:
        return None
    signal_line = np.array(ema_series(macd_line.tolist(), signal_period))
    offset = len(macd_line) - len(signal_line)
    macd_aligned = macd_line[offset:]
    histogram = macd_aligned - signal_line
    return macd_aligned.tolist(), signal_line.tolist(), histogram.tolist()


# ── Momentum / Oscillators ───────────────────────────────────────────────


def rate_of_change(values: list[float], period: int = 10) -> float | None:
    if period <= 0 or len(values) <= period:
        return None
    arr = _arr(values)
    previous = arr[-period - 1]
    if previous == 0:
        return None
    return float((arr[-1] - previous) / previous * 100.0)


def rsi(values: list[float], period: int = 14) -> float | None:
    if period <= 0 or len(values) <= period:
        return None
    arr = _arr(values)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    if len(gains) < period:
        return None
    avg_gain = np.sum(gains[:period]) / period
    avg_loss = np.sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def rsi_series(values: list[float], period: int = 14) -> list[float]:
    if period <= 0 or len(values) <= period:
        return []
    arr = _arr(values)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    if len(gains) < period:
        return []

    result: list[float] = []
    avg_gain = np.sum(gains[:period]) / period
    avg_loss = np.sum(losses[:period]) / period

    result.append(100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss)))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result.append(100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss)))

    return [float("nan")] * period + result


def realized_volatility_pct(values: list[float], period: int = 20) -> float | None:
    if period <= 1 or len(values) <= period:
        return None
    arr = _arr(values)
    window = arr[-(period + 1) :]
    returns = np.log(window[1:] / window[:-1])
    valid = returns[np.isfinite(returns) & (window[1:] > 0) & (window[:-1] > 0)]
    if len(valid) < 2:
        return None
    mean = np.mean(valid)
    variance = np.sum((valid - mean) ** 2) / len(valid)
    return float(math.sqrt(variance) * 100.0)


# ── Extremes ───────────────────────────────────────────────────────────────


def highest(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return float(np.max(_arr(values)[-period:]))


def lowest(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return float(np.min(_arr(values)[-period:]))


# ── ATR ──────────────────────────────────────────────────────────────────


def atr(candles: list[Candle], period: int = 14) -> float | None:
    if period <= 0 or len(candles) <= period:
        return None
    _, highs, lows, closes, _ = _ohlcv(candles)
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(np.maximum(tr1, tr2), tr3)
    if len(tr) < period:
        return None
    return float(np.mean(tr[-period:]))


def atr_series(candles: list[Candle], period: int = 14) -> list[float]:
    if period <= 0 or len(candles) <= period:
        return []
    _, highs, lows, closes, _ = _ohlcv(candles)
    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(np.maximum(tr1, tr2), tr3)
    if len(tr) < period:
        return []
    kernel = np.ones(period) / period
    result = np.convolve(tr, kernel, mode="valid")
    padded = np.full(len(tr), np.nan)
    padded[period - 1 :] = result
    return [float("nan")] + padded.tolist()


# ── Bollinger Bands ──────────────────────────────────────────────────────


def bollinger_bands(
    values: list[float], period: int = 20, deviations: float = 2.0
) -> tuple[float, float, float] | None:
    if period <= 1 or len(values) < period:
        return None
    arr = _arr(values)
    window = arr[-period:]
    middle = float(np.mean(window))
    deviation = float(np.std(window)) * deviations
    return middle - deviation, middle, middle + deviation


def bollinger_bands_series(
    values: list[float], period: int = 20, deviations: float = 2.0
) -> tuple[list[float], list[float], list[float]] | None:
    if period <= 1 or len(values) < period:
        return None
    arr = _arr(values)
    kernel = np.ones(period) / period
    middles = np.convolve(arr, kernel, mode="valid")
    squared = np.convolve(arr**2, kernel, mode="valid")
    variances = np.maximum(squared - middles**2, 0.0)
    stds = np.sqrt(variances) * deviations
    lowers = middles - stds
    uppers = middles + stds
    lowers_padded = np.full(len(arr), np.nan)
    uppers_padded = np.full(len(arr), np.nan)
    middles_padded = np.full(len(arr), np.nan)
    lowers_padded[period - 1 :] = lowers
    middles_padded[period - 1 :] = middles
    uppers_padded[period - 1 :] = uppers
    return lowers_padded.tolist(), middles_padded.tolist(), uppers_padded.tolist()


# ── Advanced Moving Averages ────────────────────────────────────────────────


def dema(values: list[float], period: int) -> float | None:
    """Double Exponential Moving Average — last value only."""
    if period <= 0 or len(values) < period:
        return None
    arr = _arr(values)
    ema1 = np.array(ema_series(arr.tolist(), period))
    ema2 = np.array(ema_series(ema1.tolist(), period))
    dema_vals = 2 * ema1 - ema2
    return float(dema_vals[-1]) if len(dema_vals) > 0 else None


def dema_series(values: list[float], period: int) -> list[float]:
    """Double Exponential Moving Average — full series."""
    if period <= 0 or not values:
        return []
    arr = _arr(values)
    ema1 = np.array(ema_series(arr.tolist(), period), dtype=np.float64)
    ema2 = np.array(ema_series(ema1.tolist(), period), dtype=np.float64)
    result = 2 * ema1 - ema2
    return result.tolist()  # type: ignore[no-any-return]


def tema(values: list[float], period: int) -> float | None:
    """Triple Exponential Moving Average — last value only."""
    if period <= 0 or len(values) < period:
        return None
    arr = _arr(values)
    ema1 = np.array(ema_series(arr.tolist(), period))
    ema2 = np.array(ema_series(ema1.tolist(), period))
    ema3 = np.array(ema_series(ema2.tolist(), period))
    tema_vals = 3 * ema1 - 3 * ema2 + ema3
    return float(tema_vals[-1]) if len(tema_vals) > 0 else None


def tema_series(values: list[float], period: int) -> list[float]:
    """Triple Exponential Moving Average — full series."""
    if period <= 0 or not values:
        return []
    arr = _arr(values)
    ema1 = np.array(ema_series(arr.tolist(), period), dtype=np.float64)
    ema2 = np.array(ema_series(ema1.tolist(), period), dtype=np.float64)
    ema3 = np.array(ema_series(ema2.tolist(), period), dtype=np.float64)
    result = 3 * ema1 - 3 * ema2 + ema3
    return result.tolist()  # type: ignore[no-any-return]


def kama(values: list[float], period: int = 10) -> float | None:
    """Kaufman Adaptive Moving Average — last value only."""
    if period <= 1 or len(values) < period + 1:
        return None
    arr = _arr(values)
    # Efficiency ratio
    change = abs(arr[-1] - arr[-period - 1])
    volatility = np.sum(np.abs(np.diff(arr[-(period + 1) :])))
    er = 1.0 if volatility == 0 else change / volatility
    # Smoothing constant
    fast_sc = 2.0 / (2 + 1)
    slow_sc = 2.0 / (30 + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    result = np.empty(len(arr), dtype=np.float64)
    result[0] = arr[0]
    for i in range(1, len(arr)):
        result[i] = result[i - 1] + sc * (arr[i] - result[i - 1])
    return float(result[-1])


def kama_series(values: list[float], period: int = 10) -> list[float]:
    """Kaufman Adaptive Moving Average — full series."""
    if period <= 1 or len(values) <= period:
        return []
    arr = _arr(values)
    change = np.abs(np.diff(arr, period))
    volatility = np.array(
        [np.sum(np.abs(np.diff(arr[i : i + period]))) for i in range(len(arr) - period)]
    )
    er = np.where(volatility > 0, change / volatility, 1.0)
    fast_sc = 2.0 / (2 + 1)
    slow_sc = 2.0 / (30 + 1)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    result = np.empty(len(arr), dtype=np.float64)
    result[0] = arr[0]
    result[1 : period + 1] = arr[1 : period + 1]
    for i in range(period + 1, len(arr)):
        result[i] = result[i - 1] + sc[i - period - 1] * (arr[i] - result[i - 1])
    return result.tolist()


def t3(values: list[float], period: int = 10, v_factor: float = 0.7) -> float | None:
    """Triple Exponential Moving Average (T3) — last value only."""
    if period <= 0 or len(values) < period:
        return None
    arr = _arr(values)
    e1 = np.array(ema_series(arr.tolist(), period))
    e2 = np.array(ema_series(e1.tolist(), period))
    e3 = np.array(ema_series(e2.tolist(), period))
    e4 = np.array(ema_series(e3.tolist(), period))
    e5 = np.array(ema_series(e4.tolist(), period))
    e6 = np.array(ema_series(e5.tolist(), period))
    c1 = -(v_factor**3)
    c2 = 3 * v_factor**2 + 3 * v_factor**3
    c3 = -6 * v_factor**2 - 3 * v_factor - 3 * v_factor**3
    c4 = 1 + 3 * v_factor + 3 * v_factor**2 + 3 * v_factor**3
    t3_vals = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
    return float(t3_vals[-1]) if len(t3_vals) > 0 else None


def t3_series(values: list[float], period: int = 10, v_factor: float = 0.7) -> list[float]:
    """Triple Exponential Moving Average (T3) — full series."""
    if period <= 0 or not values:
        return []
    arr = _arr(values)
    e1 = np.array(ema_series(arr.tolist(), period), dtype=np.float64)
    e2 = np.array(ema_series(e1.tolist(), period), dtype=np.float64)
    e3 = np.array(ema_series(e2.tolist(), period), dtype=np.float64)
    e4 = np.array(ema_series(e3.tolist(), period), dtype=np.float64)
    e5 = np.array(ema_series(e4.tolist(), period), dtype=np.float64)
    e6 = np.array(ema_series(e5.tolist(), period), dtype=np.float64)
    c1 = -(v_factor**3)
    c2 = 3 * v_factor**2 + 3 * v_factor**3
    c3 = -6 * v_factor**2 - 3 * v_factor - 3 * v_factor**3
    c4 = 1 + 3 * v_factor + 3 * v_factor**2 + 3 * v_factor**3
    result = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
    return result.tolist()  # type: ignore[no-any-return]


# ── VWAP ───────────────────────────────────────────────────────────────────


def vwap(candles: list[Candle], period: int | None = None) -> float | None:
    window = candles[-period:] if period else candles
    total_volume = sum(item.volume for item in window)
    if not window or total_volume <= 0:
        return None
    typical = np.array([(c.high + c.low + c.close) / 3.0 for c in window], dtype=np.float64)
    vols = np.array([c.volume for c in window], dtype=np.float64)
    return float(np.sum(typical * vols) / np.sum(vols))


def vwap_series(candles: list[Candle], period: int | None = None) -> list[float]:
    if not candles:
        return []
    window = candles[-period:] if period else candles
    typicals = np.array([(c.high + c.low + c.close) / 3.0 for c in window], dtype=np.float64)
    vols = np.array([c.volume for c in window], dtype=np.float64)
    cum_typical_vol = np.cumsum(typicals * vols)
    cum_vol = np.cumsum(vols)
    result = cum_typical_vol / cum_vol
    return result.tolist()  # type: ignore[no-any-return]


# ── ADX ──────────────────────────────────────────────────────────────────


def adx(candles: list[Candle], period: int = 14) -> float | None:
    if period <= 1 or len(candles) < (period * 2 + 1):
        return None
    _, highs, lows, closes, _ = _ohlcv(candles)

    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(np.maximum(tr1, tr2), tr3)

    up_move = highs[1:] - highs[:-1]
    down_move = lows[:-1] - lows[1:]
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    if len(tr) < period:
        return None

    smooth_tr = np.sum(tr[:period])
    smooth_plus = np.sum(plus_dm[:period])
    smooth_minus = np.sum(minus_dm[:period])

    dx_values: list[float] = []
    for i in range(period, len(tr)):
        if i > period:
            smooth_tr = smooth_tr - (smooth_tr / period) + tr[i]
            smooth_plus = smooth_plus - (smooth_plus / period) + plus_dm[i]
            smooth_minus = smooth_minus - (smooth_minus / period) + minus_dm[i]
        if smooth_tr <= 0:
            dx_values.append(0.0)
            continue
        plus_di = 100 * smooth_plus / smooth_tr
        minus_di = 100 * smooth_minus / smooth_tr
        denominator = plus_di + minus_di
        dx_values.append(0.0 if denominator == 0 else 100.0 * abs(plus_di - minus_di) / denominator)

    if len(dx_values) < period:
        return None
    value = float(np.sum(dx_values[:period]) / period)
    for dx_value in dx_values[period:]:
        value = ((value * (period - 1)) + dx_value) / period
    return float(value)


# ── Ichimoku ───────────────────────────────────────────────────────────────


def ichimoku(
    candles: list[Candle],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> tuple[float, float, float, float] | None:
    if len(candles) < senkou_b_period:
        return None

    def _hl2(window: list[Candle]) -> float:
        return (max(c.high for c in window) + min(c.low for c in window)) / 2.0

    tenkan_sen = _hl2(candles[-tenkan_period:])
    kijun_sen = _hl2(candles[-kijun_period:])
    senkou_span_a = (tenkan_sen + kijun_sen) / 2.0
    senkou_span_b = _hl2(candles[-senkou_b_period:])
    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b


# ── Drawdown ───────────────────────────────────────────────────────────────


def max_drawdown_pct(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    arr = _arr(equity_curve)
    running_max = np.maximum.accumulate(arr)
    drawdown = (running_max - arr) / np.where(running_max > 0, running_max, 1.0) * 100.0
    return float(np.max(drawdown))


def max_drawdown_series(equity_curve: list[float]) -> list[float]:
    if not equity_curve:
        return []
    arr = _arr(equity_curve)
    running_max = np.maximum.accumulate(arr)
    drawdown = (running_max - arr) / np.where(running_max > 0, running_max, 1.0) * 100.0
    return drawdown.tolist()  # type: ignore[no-any-return]


# ── Momentum Oscillators ───────────────────────────────────────────────────


def apo(values: list[float], fast_period: int = 12, slow_period: int = 26) -> float | None:
    """Absolute Price Oscillator — last value only."""
    if fast_period <= 0 or slow_period <= fast_period or len(values) < slow_period:
        return None
    arr = _arr(values)
    fast_ema = np.array(ema_series(arr.tolist(), fast_period))
    slow_ema = np.array(ema_series(arr.tolist(), slow_period))
    return float(fast_ema[-1] - slow_ema[-1])


def apo_series(values: list[float], fast_period: int = 12, slow_period: int = 26) -> list[float]:
    """Absolute Price Oscillator — full series."""
    if fast_period <= 0 or slow_period <= fast_period or len(values) < slow_period:
        return []
    arr = _arr(values)
    fast_ema = np.array(ema_series(arr.tolist(), fast_period), dtype=np.float64)
    slow_ema = np.array(ema_series(arr.tolist(), slow_period), dtype=np.float64)
    result = fast_ema - slow_ema
    return result.tolist()  # type: ignore[no-any-return]


def cci(candles: list[Candle], period: int = 14) -> float | None:
    """Commodity Channel Index — last value only."""
    if period <= 0 or len(candles) < period:
        return None
    _, highs, lows, closes, _ = _ohlcv(candles)
    typical = (highs + lows + closes) / 3.0
    sma_tp = np.convolve(typical, np.ones(period) / period, mode="valid")
    if len(sma_tp) < period:
        return None
    mean_dev = np.mean(np.abs(typical[-period:] - sma_tp[-1]))
    if mean_dev == 0:
        return 0.0
    return float((typical[-1] - sma_tp[-1]) / (0.015 * mean_dev))


def mfi(candles: list[Candle], period: int = 14) -> float | None:
    """Money Flow Index — last value only."""
    if period <= 0 or len(candles) < period + 1:
        return None
    _, highs, lows, closes, volumes = _ohlcv(candles)
    typical = (highs + lows + closes) / 3.0
    money_flow = typical * volumes
    positive_flow = np.where(closes[1:] > closes[:-1], money_flow[1:], 0.0)
    negative_flow = np.where(closes[1:] < closes[:-1], money_flow[1:], 0.0)
    if len(positive_flow) < period:
        return None
    pos_sum = np.sum(positive_flow[-period:])
    neg_sum = np.sum(negative_flow[-period:])
    if neg_sum == 0:
        return 100.0
    mfr = pos_sum / neg_sum
    return float(100.0 - (100.0 / (1.0 + mfr)))


def ppo(
    values: list[float], fast_period: int = 12, slow_period: int = 26
) -> tuple[float, float] | None:
    """Percentage Price Oscillator — (MACD line, signal line) last values."""
    if fast_period <= 0 or slow_period <= fast_period or len(values) < slow_period:
        return None
    arr = _arr(values)
    fast_ema = np.array(ema_series(arr.tolist(), fast_period))
    slow_ema = np.array(ema_series(arr.tolist(), slow_period))
    if len(fast_ema) == 0 or len(slow_ema) == 0 or slow_ema[-1] == 0:
        return None
    ppo_line = (fast_ema - slow_ema) / slow_ema * 100.0
    signal_line = np.array(ema_series(ppo_line.tolist(), 9))
    return float(ppo_line[-1]), float(signal_line[-1])


def roc(values: list[float], period: int = 10) -> float | None:
    """Rate of Change — percentage change from period bars ago."""
    if period <= 0 or len(values) <= period:
        return None
    arr = _arr(values)
    previous = arr[-period - 1]
    if previous == 0:
        return None
    return float((arr[-1] - previous) / previous * 100.0)


def rocp(values: list[float], period: int = 10) -> float | None:
    """Rate of Change Percentage — same as ROC."""
    return roc(values, period)


def rocr(values: list[float], period: int = 10) -> float | None:
    """Rate of Change Ratio — current / previous."""
    if period <= 0 or len(values) <= period:
        return None
    arr = _arr(values)
    previous = arr[-period - 1]
    if previous == 0:
        return None
    return float(arr[-1] / previous)


# ── Volume Indicators ──────────────────────────────────────────────────────


def obv(candles: list[Candle]) -> float | None:
    """On-Balance Volume — last value only."""
    if not candles:
        return None
    _, _, _, closes, volumes = _ohlcv(candles)
    if len(closes) < 2:
        return float(volumes[0]) if len(volumes) > 0 else 0.0
    direction = np.where(closes[1:] > closes[:-1], volumes[1:], 0.0)
    direction = np.where(closes[1:] < closes[:-1], -volumes[1:], direction)
    return float(np.sum(direction) + volumes[0])


def obv_series(candles: list[Candle]) -> list[float]:
    """On-Balance Volume — full series."""
    if not candles:
        return []
    _, highs, lows, closes, volumes = _ohlcv(candles)
    if len(closes) < 2:
        return [float(volumes[0])] if len(volumes) > 0 else []
    direction = np.where(closes[1:] > closes[:-1], volumes[1:], 0.0)
    direction = np.where(closes[1:] < closes[:-1], -volumes[1:], direction)
    obv_vals = np.concatenate([[volumes[0]], np.cumsum(direction)])
    return obv_vals.tolist()  # type: ignore[no-any-return]


# ── Volatility Indicators ──────────────────────────────────────────────────


def natr(candles: list[Candle], period: int = 14) -> float | None:
    """Normalized Average True Range — last value only."""
    if period <= 0 or len(candles) <= period:
        return None
    atr_val = atr(candles, period)
    if atr_val is None:
        return None
    _, _, _, closes, _ = _ohlcv(candles)
    if closes[-1] == 0:
        return None
    return float(atr_val / closes[-1] * 100.0)


def trange(candles: list[Candle]) -> float | None:
    """True Range — last value only."""
    if len(candles) < 2:
        return None
    _, highs, lows, closes, _ = _ohlcv(candles)
    tr1 = highs[-1] - lows[-1]
    tr2 = abs(highs[-1] - closes[-2])
    tr3 = abs(lows[-1] - closes[-2])
    return float(max(tr1, tr2, tr3))


# ── Statistical Functions ──────────────────────────────────────────────────


def stddev(values: list[float], period: int = 20) -> float | None:
    """Standard Deviation — last value only."""
    if period <= 1 or len(values) < period:
        return None
    arr = _arr(values)
    return float(np.std(arr[-period:]))


def linear_reg(values: list[float], period: int = 14) -> float | None:
    """Linear Regression — last value only."""
    if period <= 1 or len(values) < period:
        return None
    arr = _arr(values)[-period:]
    x = np.arange(len(arr))
    slope, intercept = np.polyfit(x, arr, 1)
    return float(slope * (period - 1) + intercept)


def linear_reg_slope(values: list[float], period: int = 14) -> float | None:
    """Linear Regression Slope — last value only."""
    if period <= 1 or len(values) < period:
        return None
    arr = _arr(values)[-period:]
    x = np.arange(len(arr))
    slope, _ = np.polyfit(x, arr, 1)
    return float(slope)


def tsf(values: list[float], period: int = 14) -> float | None:
    """Time Series Forecast — last value only."""
    if period <= 1 or len(values) < period:
        return None
    arr = _arr(values)[-period:]
    x = np.arange(len(arr))
    slope, intercept = np.polyfit(x, arr, 1)
    return float(slope * period + intercept)


def variance(values: list[float], period: int = 20) -> float | None:
    """Variance — last value only."""
    if period <= 1 or len(values) < period:
        return None
    arr = _arr(values)
    return float(np.var(arr[-period:]))


# ── Price Transform ──────────────────────────────────────────────────────


def avg_price(candles: list[Candle]) -> float | None:
    """Average Price — (high + low + close) / 3 — last value."""
    if not candles:
        return None
    _, highs, lows, closes, _ = _ohlcv(candles)
    return float(np.mean((highs[-1] + lows[-1] + closes[-1]) / 3.0))


def median_price(candles: list[Candle]) -> float | None:
    """Median Price — (high + low) / 2 — last value."""
    if not candles:
        return None
    _, highs, lows, _, _ = _ohlcv(candles)
    return float((highs[-1] + lows[-1]) / 2.0)


def typical_price(candles: list[Candle]) -> float | None:
    """Typical Price — (high + low + close) / 3 — last value."""
    if not candles:
        return None
    _, highs, lows, closes, _ = _ohlcv(candles)
    return float((highs[-1] + lows[-1] + closes[-1]) / 3.0)


def weighted_close(candles: list[Candle]) -> float | None:
    """Weighted Close Price — (high + low + close + close) / 4 — last value."""
    if not candles:
        return None
    _, highs, lows, closes, _ = _ohlcv(candles)
    return float((highs[-1] + lows[-1] + 2 * closes[-1]) / 4.0)


# ── Stochastic Oscillator ──────────────────────────────────────────────────


def stochastic_oscillator(
    candles: list[Candle], k_period: int = 14, d_period: int = 3
) -> tuple[float, float] | None:
    if k_period <= 0 or d_period <= 0 or len(candles) < k_period:
        return None
    window = candles[-k_period:]
    high = max(c.high for c in window)
    low = min(c.low for c in window)
    close = window[-1].close
    if high == low:
        return None
    k_val = (close - low) / (high - low) * 100.0
    return k_val, k_val


# ── Williams %R ────────────────────────────────────────────────────────────


def williams_r(candles: list[Candle], period: int = 14) -> float | None:
    if period <= 0 or len(candles) < period:
        return None
    window = candles[-period:]
    high = max(c.high for c in window)
    low = min(c.low for c in window)
    close = candles[-1].close
    if high == low:
        return None
    return float((high - close) / (high - low) * -100.0)
