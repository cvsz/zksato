from __future__ import annotations

from zksato.domain import Signal, SignalAction, StrategyConfig
from zksato.indicators import ema, highest, rsi


class StrategyEngine:
    """Deterministic signal generation shared by live-paper automation and backtests."""

    def evaluate(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        price = prices[-1] if prices else 0.0
        if price <= 0:
            raise ValueError("strategy requires at least one positive price")
        if len(prices) < config.min_history:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=price,
                confidence=0.0,
                reason=f"waiting for history ({len(prices)}/{config.min_history})",
            )
        if config.name == "ema_cross":
            return self._ema_cross(symbol, prices, config)
        if config.name == "rsi_reversion":
            return self._rsi_reversion(symbol, prices, config)
        if config.name == "breakout":
            return self._breakout(symbol, prices, config)
        raise ValueError(f"unknown strategy: {config.name}")

    def _ema_cross(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        fast = ema(prices, config.fast_period)
        slow = ema(prices, config.slow_period)
        prev_fast = ema(prices[:-1], config.fast_period)
        prev_slow = ema(prices[:-1], config.slow_period)
        price = prices[-1]
        if None in {fast, slow, prev_fast, prev_slow}:
            action = SignalAction.HOLD
            reason = "insufficient EMA history"
            confidence = 0.0
        elif prev_fast <= prev_slow and fast > slow:
            action = SignalAction.BUY
            reason = f"EMA{config.fast_period} crossed above EMA{config.slow_period}"
            confidence = min(abs(fast - slow) / price * 20, 1.0)
        elif prev_fast >= prev_slow and fast < slow:
            action = SignalAction.SELL
            reason = f"EMA{config.fast_period} crossed below EMA{config.slow_period}"
            confidence = min(abs(fast - slow) / price * 20, 1.0)
        else:
            action = SignalAction.HOLD
            reason = "no EMA crossover"
            confidence = 0.25
        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=action,
            price=price,
            confidence=confidence,
            reason=reason,
        )

    def _rsi_reversion(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        value = rsi(prices, config.rsi_period)
        price = prices[-1]
        if value is None:
            action = SignalAction.HOLD
            reason = "insufficient RSI history"
            confidence = 0.0
        elif value <= config.rsi_buy:
            action = SignalAction.BUY
            reason = f"RSI {value:.1f} <= {config.rsi_buy:.1f}"
            confidence = min((config.rsi_buy - value + 10) / 30, 1.0)
        elif value >= config.rsi_sell:
            action = SignalAction.SELL
            reason = f"RSI {value:.1f} >= {config.rsi_sell:.1f}"
            confidence = min((value - config.rsi_sell + 10) / 30, 1.0)
        else:
            action = SignalAction.HOLD
            reason = f"RSI neutral at {value:.1f}"
            confidence = 0.25
        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=action,
            price=price,
            confidence=confidence,
            reason=reason,
        )

    def _breakout(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        price = prices[-1]
        previous = prices[:-1]
        upper = highest(previous, config.breakout_period)
        if upper is None:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=price,
                confidence=0.0,
                reason="insufficient breakout history",
            )
        if price > upper:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=min(((price - upper) / upper) * 20 + 0.5, 1.0),
                reason=f"price broke above {config.breakout_period}-period high {upper:.2f}",
            )
        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.25,
            reason=f"below breakout level {upper:.2f}",
        )
