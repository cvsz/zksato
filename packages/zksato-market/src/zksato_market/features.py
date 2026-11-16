"""Market technical indicators and feature builders for zksato.

Adapted from anglerfish-fable5 autotrade.py build_market_features() and
zksato src/zksato/indicators.py. All functions are NumPy-vectorized for
performance and serve as signal generators only — no order execution.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _arr(values: list[float]) -> np.ndarray:
    """Convert a list of floats to a NumPy array, safely handling empty lists."""
    if not values:
        return np.array([], dtype=np.float64)
    return np.asarray(values, dtype=np.float64)


# ---------------------------------------------------------------------------
# Moving Averages
# ---------------------------------------------------------------------------


def sma(values: list[float], period: int) -> float | None:
    """Simple Moving Average of `period` values — last window average."""
    if period <= 0 or len(values) < period:
        return None
    return float(np.mean(_arr(values)[-period:]))


def sma_series(values: list[float], period: int) -> list[float]:
    """Full SMA series (NumPy convolution-based, efficient)."""
    if period <= 0 or len(values) < period:
        return []
    arr = _arr(values)
    kernel = np.ones(period) / period
    result = np.convolve(arr, kernel, mode="valid")
    padded = np.full(len(arr), np.nan)
    padded[period - 1 :] = result
    return padded.tolist()


def ema(values: list[float], period: int) -> float | None:
    """Exponential Moving Average — last value only."""
    if period <= 0 or len(values) < period:
        return None
    arr = _arr(values)
    alpha = 2.0 / (period + 1.0)
    result = np.empty(len(arr), dtype=np.float64)
    result[0] = arr[0]
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1.0 - alpha) * result[i - 1]
    return float(result[-1])


def ema_series(values: list[float], period: int) -> list[float]:
    """Full EMA series."""
    if period <= 0 or not values:
        return []
    arr = _arr(values)
    alpha = 2.0 / (period + 1.0)
    result = np.empty(len(arr), dtype=np.float64)
    result[0] = arr[0]
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1.0 - alpha) * result[i - 1]
    return result.tolist()


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------


def macd(
    values: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[float, float, float] | None:
    """MACD (fast EMA - slow EMA, signal line, histogram) — last values."""
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
    # Signal line on MACD line
    signal_alpha = 2.0 / (signal_period + 1.0)
    signal_line = np.empty(len(macd_line), dtype=np.float64)
    signal_line[0] = macd_line[0]
    for i in range(1, len(macd_line)):
        signal_line[i] = signal_alpha * macd_line[i] + (1.0 - signal_alpha) * signal_line[i - 1]
    histogram = float(macd_line[-1] - signal_line[-1])
    return float(macd_line[-1]), float(signal_line[-1]), histogram


def macd_series(
    values: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float], list[float], list[float]] | None:
    """Full MACD series (macd_line, signal_line, histogram)."""
    if fast_period <= 0 or slow_period <= fast_period or signal_period <= 0:
        return None
    if len(values) < slow_period + signal_period:
        return None
    arr = _arr(values)
    fast_ema = np.array(ema_series(arr.tolist(), fast_period))
    slow_ema = np.array(ema_series(arr.tolist(), slow_period))
    macd_line = fast_ema - slow_ema
    if len(macd_line) < signal_period:
        return None, None, None

    # Signal line on MACD line
    signal_alpha = 2.0 / (signal_period + 1.0)
    signal_line = np.empty(len(macd_line), dtype=np.float64)
    signal_line[0] = macd_line[0]
    for i in range(1, len(macd_line)):
        signal_line[i] = signal_alpha * macd_line[i] + (1.0 - signal_alpha) * signal_line[i - 1]

    offset = len(macd_line) - len(signal_line)
    macd_aligned = macd_line[offset:]
    histogram = [macd_aligned[i] - signal_line[i] for i in range(len(signal_line))]
    return macd_aligned.tolist(), signal_line.tolist(), histogram


# ---------------------------------------------------------------------------
# Momentum / Oscillators
# ---------------------------------------------------------------------------


def rsi(values: list[float], period: int = 14) -> float | None:
    """Relative Strength Index — standard Wilder smoothing (simple version)."""
    if period <= 0 or len(values) < period + 1:
        return None
    arr = _arr(values)
    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Rolling average using cumulative smoothing (Wilder's method)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if len(gains) > period:
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1.0 + rs)))


def rsi_series(values: list[float], period: int = 14) -> list[float]:
    """Full RSI series."""
    if period <= 0 or len(values) < period:
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


def macd_histogram(
    values: list[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> float | None:
    """MACD histogram last value only."""
    result = macd(values, fast_period, slow_period, signal_period)
    if result is None:
        return None
    return result[2]


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


def bollinger_bands(
    values: list[float], period: int = 20, deviations: float = 2.0
) -> tuple[float, float, float] | None:
    """Bollinger Bands — (lower, middle, upper) last values."""
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
    """Full Bollinger Bands series (lower, middle, upper)."""
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
    # Pad to full length
    lowers_padded = np.full(len(arr), np.nan)
    uppers_padded = np.full(len(arr), np.nan)
    middles_padded = np.full(len(arr), np.nan)
    lowers_padded[period - 1 :] = lowers
    middles_padded[period - 1 :] = middles
    uppers_padded[period - 1 :] = uppers
    return lowers_padded.tolist(), middles_padded.tolist(), uppers_padded.tolist()


# ---------------------------------------------------------------------------
# ATR (Average True Range)
# ---------------------------------------------------------------------------


def atr(candles: list[Any], period: int = 14) -> float | None:
    """Average True Range — last value only.

    Expects a list of candle objects/dicts with .high/.low/.close attributes,
    or dict-like entries with keys 'high', 'low', 'close'.
    """
    if period <= 0 or len(candles) <= period:
        return None

    # Extract highs, lows, closes as float arrays
    highs = np.array(
        [float(c.get("high", c.high) if hasattr(c, "high") else c["high"]) for c in candles],
        dtype=np.float64,
    )
    lows = np.array(
        [float(c.get("low", c.low) if hasattr(c, "low") else c["low"]) for c in candles],
        dtype=np.float64,
    )
    closes = np.array(
        [float(c.get("close", c.close) if hasattr(c, "close") else c["close"]) for c in candles],
        dtype=np.float64,
    )

    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(np.maximum(tr1, tr2), tr3)

    if len(tr) < period:
        return None
    return float(np.mean(tr[-period:]))


def atr_series(candles: list[Any], period: int = 14) -> list[float]:
    """Full ATR series."""
    if period <= 0 or len(candles) <= period:
        return []
    highs = np.array(
        [float(c.get("high", c.high) if hasattr(c, "high") else c["high"]) for c in candles],
        dtype=np.float64,
    )
    lows = np.array(
        [float(c.get("low", c.low) if hasattr(c, "low") else c["low"]) for c in candles],
        dtype=np.float64,
    )
    closes = np.array(
        [float(c.get("close", c.close) if hasattr(c, "close") else c["close"]) for c in candles],
        dtype=np.float64,
    )

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
    return [float("nan"), *padded.tolist()]


# ---------------------------------------------------------------------------
# VWAP (Volume Weighted Average Price)
# ---------------------------------------------------------------------------


def _vwap_typical_price(c: dict[str, Any]) -> float:
    """Compute typical price = (high + low + close) / 3 for a single candle."""
    high = c.get("high", c["high"])
    low = c.get("low", c["low"])
    close = c.get("close", c["close"])
    return float((high + low + close) / 3.0)


def vwap(candles: list[Any], period: int | None = None) -> float | None:
    """Volume Weighted Average Price — last value only."""
    window = candles[-period:] if period else candles
    if not window:
        return None
    total_volume = sum(
        float(c.get("volume", c.volume if hasattr(c, "volume") else c["volume"])) for c in window
    )
    if total_volume <= 0:
        return None
    typical = np.array([_vwap_typical_price(c) for c in window], dtype=np.float64)
    vols = np.array(
        [float(c.get("volume", c.volume if hasattr(c, "volume") else c["volume"])) for c in window],
        dtype=np.float64,
    )
    return float(np.sum(typical * vols) / np.sum(vols))


def vwap_series(candles: list[Any], period: int | None = None) -> list[float]:
    """Full VWAP series."""
    if not candles:
        return []
    window = candles[-period:] if period else candles
    typicals = np.array([_vwap_typical_price(c) for c in window], dtype=np.float64)
    vols = np.array(
        [float(c.get("volume", c.volume if hasattr(c, "volume") else c["volume"])) for c in window],
        dtype=np.float64,
    )
    cum_typical_vol = np.cumsum(typicals * vols)
    cum_vol = np.cumsum(vols)
    result = cum_typical_vol / cum_vol
    return [float(x) for x in result]


# ---------------------------------------------------------------------------
# Williams %R
# ---------------------------------------------------------------------------


def williams_r(candles: list[Any], period: int = 14) -> float | None:
    """Williams %R — last value only."""
    if period <= 0 or len(candles) < period:
        return None
    window = candles[-period:]
    highs = [float(c.get("high", c.high) if hasattr(c, "high") else c["high"]) for c in window]
    lows = [float(c.get("low", c.low) if hasattr(c, "low") else c["low"]) for c in window]
    closes = [float(c.get("close", c.close) if hasattr(c, "close") else c["close"]) for c in window]
    high = max(highs)
    low = min(lows)
    close = closes[-1]
    if high == low:
        return None
    return float((high - close) / (high - low) * -100.0)


def williams_r_series(candles: list[Any], period: int = 14) -> list[float]:
    """Full Williams %R series."""
    if period <= 0 or len(candles) < period:
        return []
    wr_values: list[float] = []
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1 : i + 1]
        highs = [float(c.get("high", c.high) if hasattr(c, "high") else c["high"]) for c in window]
        lows = [float(c.get("low", c.low) if hasattr(c, "low") else c["low"]) for c in window]
        closes = [
            float(c.get("close", c.close) if hasattr(c, "close") else c["close"]) for c in window
        ]
        high = max(highs)
        low = min(lows)
        close = closes[-1]
        if high == low:
            wr_values.append(-50.0)
        else:
            wr_values.append(float((high - close) / (high - low) * -100.0))
    return wr_values


# ---------------------------------------------------------------------------
# Stochastic Oscillator
# ---------------------------------------------------------------------------


def stochastic_oscillator(
    candles: list[Any], k_period: int = 14, d_period: int = 3
) -> tuple[float, float] | None:
    """Stochastic Oscillator (%K, %D) — last values only."""
    if k_period <= 0 or d_period <= 0 or len(candles) < k_period:
        return None
    window = candles[-k_period:]
    high = max(float(c.get("high", c.high) if hasattr(c, "high") else c["high"]) for c in window)
    low = min(float(c.get("low", c.low) if hasattr(c, "low") else c["low"]) for c in window)
    close = float(
        window[-1].get("close", window[-1].close)
        if hasattr(window[-1], "close")
        else window[-1]["close"]
    )
    if high == low:
        return 50.0, 50.0
    k_val = (close - low) / (high - low) * 100.0
    # %D is the simple moving average of %K over d_period
    # Reuse a window for %D calculation
    k_values: list[float] = []
    for i in range(k_period - 1, len(candles)):
        w = candles[i - k_period + 1 : i + 1]
        h = max(float(c.get("high", c.high) if hasattr(c, "high") else c["high"]) for c in w)
        lowest = min(float(c.get("low", c.low) if hasattr(c, "low") else c["low"]) for c in w)
        c_ = float(
            candles[i].get("close", candles[i].close)
            if hasattr(candles[i], "close")
            else candles[i]["close"]
        )
        if h == lowest:
            k_values.append(50.0)
        else:
            k_values.append((c_ - lowest) / (h - lowest) * 100.0)
    if len(k_values) < d_period:
        return k_val, k_val
    d_start = len(k_values) - d_period
    d_val = sum(k_values[d_start : d_start + d_period]) / d_period
    return k_val, d_val


# ---------------------------------------------------------------------------
# build_market_features — the core LLM-feeding feature dict
# ---------------------------------------------------------------------------


def build_market_features(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    last_price: float,
    ticker: dict[str, Any] | None = None,
    candles: list[Any] | None = None,
) -> dict[str, Any]:
    """Build lightweight market features from OHLCV + ticker for LLM consumption.

    Adapted from anglerfish-fable5 autotrade.py build_market_features().
    The schema is compact and LLM-friendly, matching the format used by
    zksato's decision engine.

    Returns a dict with the following keys:
    - last_price: float
    - sma20: float | None
    - sma50: float | None
    - ema20: float | None
    - ema50: float | None
    - rsi14: float | None
    - macd: tuple[float, float, float] | None  (macd_line, signal_line, histogram)
    - macd_hist: float | None
    - bb_lower: float | None
    - bb_middle: float | None
    - bb_upper: float | None
    - atr14: float | None
    - williams_r: float | None
    - stoch_k: float | None
    - stoch_d: float | None
    - recent_high: float | None
    - recent_low: float | None
    - pct_change_last_candle: float | None
    - candles_used: int
    """
    # Use provided candles if available, otherwise construct from OHLCV arrays
    if candles is None:
        candles = [
            {"open": open_, "high": high, "low": low, "close": close, "volume": 0}
            for open_, high, low, close in zip(
                [0.0] * len(closes), highs, lows, closes, strict=False
            )
        ]

    lookback_n = min(24, len(closes))
    change_n = _pct_change_closes(closes[-lookback_n], closes[-1]) if lookback_n >= 2 else None

    # Compute indicators
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    rsi14 = rsi(closes, 14)

    macd_result = macd(closes, 12, 26, 9)
    macd_hist = macd_histogram(closes, 12, 26, 9) if macd_result is None else macd_result[2]

    bb = bollinger_bands(closes, 20, 2.0)
    bb_lower = bb[0] if bb else None
    bb_middle = bb[1] if bb else None
    bb_upper = bb[2] if bb else None

    atr14 = atr(candles, 14) if candles else None

    wr = williams_r(candles, 14) if candles else None

    stoch = stochastic_oscillator(candles, 14, 3) if candles else (50.0, 50.0)
    stoch_k = stoch[0] if stoch else 50.0
    stoch_d = stoch[1] if stoch else 50.0

    recent_high = round(max(highs), 8) if highs else None
    recent_low = round(min(lows), 8) if lows else None
    pct_change_last_candle = (
        _pct_change_closes(closes[-2], closes[-1]) if len(closes) >= 2 else None
    )

    features = {
        "last_price": round(last_price, 8) if last_price > 0 else None,
        "sma20": round(sma20, 8) if sma20 is not None else None,
        "sma50": round(sma50, 8) if sma50 is not None else None,
        "ema20": round(ema20, 8) if ema20 is not None else None,
        "ema50": round(ema50, 8) if ema50 is not None else None,
        "rsi14": round(rsi14, 2) if rsi14 is not None else None,
        "macd_hist": round(macd_hist, 8) if macd_hist is not None else None,
        "bb_lower": round(bb_lower, 8) if bb_lower is not None else None,
        "bb_middle": round(bb_middle, 8) if bb_middle is not None else None,
        "bb_upper": round(bb_upper, 8) if bb_upper is not None else None,
        "atr14": round(atr14, 8) if atr14 is not None else None,
        "williams_r": round(wr, 2) if wr is not None else None,
        "stoch_k": round(stoch_k, 2) if stoch_k is not None else None,
        "stoch_d": round(stoch_d, 2) if stoch_d is not None else None,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "pct_change_last_candle": round(pct_change_last_candle, 3)
        if pct_change_last_candle is not None
        else None,
        "pct_change_last_24_candles": round(change_n, 3) if change_n is not None else None,
        "candles_used": len(closes),
    }
    return features


def _pct_change_closes(old: float, new: float) -> float | None:
    """Percentage change from old to new price."""
    if old == 0:
        return None
    return ((new - old) / old) * 100.0
