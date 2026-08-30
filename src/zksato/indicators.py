from __future__ import annotations

import math

from zksato.domain import Candle


def sma(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if period <= 0 or not values:
        return []
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append((value * alpha) + (result[-1] * (1 - alpha)))
    return result


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return ema_series(values, period)[-1]


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
    fast = ema_series(values, fast_period)
    slow = ema_series(values, slow_period)
    line = [fast[index] - slow[index] for index in range(slow_period - 1, len(values))]
    signal = ema(line, signal_period)
    if signal is None:
        return None
    value = line[-1]
    return value, signal, value - signal


def rate_of_change(values: list[float], period: int = 10) -> float | None:
    if period <= 0 or len(values) <= period:
        return None
    previous = values[-period - 1]
    if previous == 0:
        return None
    return (values[-1] - previous) / previous * 100


def realized_volatility_pct(values: list[float], period: int = 20) -> float | None:
    if period <= 1 or len(values) <= period:
        return None
    window = values[-(period + 1) :]
    returns: list[float] = []
    for previous, current in zip(window, window[1:], strict=False):
        if previous <= 0 or current <= 0:
            return None
        returns.append(math.log(current / previous))
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / len(returns)
    return math.sqrt(variance) * 100


def rsi(values: list[float], period: int = 14) -> float | None:
    if period <= 0 or len(values) <= period:
        return None
    deltas = [current - previous for previous, current in zip(values, values[1:], strict=False)]
    gains = [max(delta, 0.0) for delta in deltas[-period:]]
    losses = [max(-delta, 0.0) for delta in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def highest(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return max(values[-period:])


def lowest(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return min(values[-period:])


def atr(candles: list[Candle], period: int = 14) -> float | None:
    if period <= 0 or len(candles) <= period:
        return None
    ranges: list[float] = []
    for previous, current in zip(candles, candles[1:], strict=False):
        ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    if len(ranges) < period:
        return None
    return sum(ranges[-period:]) / period


def bollinger_bands(
    values: list[float], period: int = 20, deviations: float = 2.0
) -> tuple[float, float, float] | None:
    if period <= 1 or len(values) < period:
        return None
    window = values[-period:]
    middle = sum(window) / period
    variance = sum((value - middle) ** 2 for value in window) / period
    deviation = math.sqrt(variance) * deviations
    return middle - deviation, middle, middle + deviation


def vwap(candles: list[Candle], period: int | None = None) -> float | None:
    window = candles[-period:] if period else candles
    total_volume = sum(item.volume for item in window)
    if not window or total_volume <= 0:
        return None
    weighted = sum(((item.high + item.low + item.close) / 3) * item.volume for item in window)
    return weighted / total_volume


def adx(candles: list[Candle], period: int = 14) -> float | None:
    if period <= 1 or len(candles) < (period * 2 + 1):
        return None
    trs: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for previous, current in zip(candles, candles[1:], strict=False):
        up_move = current.high - previous.high
        down_move = previous.low - current.low
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        trs.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    smooth_tr = sum(trs[:period])
    smooth_plus = sum(plus_dm[:period])
    smooth_minus = sum(minus_dm[:period])
    dx_values: list[float] = []
    for index in range(period, len(trs)):
        if index > period:
            smooth_tr = smooth_tr - (smooth_tr / period) + trs[index]
            smooth_plus = smooth_plus - (smooth_plus / period) + plus_dm[index]
            smooth_minus = smooth_minus - (smooth_minus / period) + minus_dm[index]
        if smooth_tr <= 0:
            dx_values.append(0.0)
            continue
        plus_di = 100 * smooth_plus / smooth_tr
        minus_di = 100 * smooth_minus / smooth_tr
        denominator = plus_di + minus_di
        dx_values.append(0.0 if denominator == 0 else 100 * abs(plus_di - minus_di) / denominator)
    if len(dx_values) < period:
        return None
    value = sum(dx_values[:period]) / period
    for dx_value in dx_values[period:]:
        value = ((value * (period - 1)) + dx_value) / period
    return value


def ichimoku(
    candles: list[Candle],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
) -> tuple[float, float, float, float] | None:
    if len(candles) < senkou_b_period:
        return None

    def _highest_lowest(window: list[Candle]) -> float:
        return (max(c.high for c in window) + min(c.low for c in window)) / 2

    tenkan_sen = _highest_lowest(candles[-tenkan_period:])
    kijun_sen = _highest_lowest(candles[-kijun_period:])
    senkou_span_a = (tenkan_sen + kijun_sen) / 2
    senkou_span_b = _highest_lowest(candles[-senkou_b_period:])

    return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b


def max_drawdown_pct(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, ((peak - value) / peak) * 100)
    return max_drawdown


def stochastic_oscillator(
    candles: list[Candle], k_period: int = 14, d_period: int = 3
) -> tuple[float, float] | None:
    """Stochastic oscillator: returns (%K, %D). Values 0–100."""
    if k_period <= 0 or d_period <= 0 or len(candles) < k_period:
        return None
    window = candles[-k_period:]
    high = max(c.high for c in window)
    low = min(c.low for c in window)
    if high == low:
        return None
    k_values: list[float] = []
    for i in range(max(0, len(candles) - k_period - d_period + 1), len(candles) - k_period + 1):
        w = candles[i : i + k_period]
        h = max(c.high for c in w)
        lo = min(c.low for c in w)
        cl = w[-1].close
        k_values.append(0.0 if h == lo else (cl - lo) / (h - lo) * 100)
    if not k_values:
        return None
    k = k_values[-1]
    d = sum(k_values[-d_period:]) / min(d_period, len(k_values))
    return k, d


def williams_r(candles: list[Candle], period: int = 14) -> float | None:
    """Williams %R: values from -100 to 0. Oversold < -80, overbought > -20."""
    if period <= 0 or len(candles) < period:
        return None
    window = candles[-period:]
    high = max(c.high for c in window)
    low = min(c.low for c in window)
    close = candles[-1].close
    if high == low:
        return None
    return (high - close) / (high - low) * -100
