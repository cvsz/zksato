"""Classic strategy implementations for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zksato_core.models import Candle, Signal, StrategyConfig
from zksato_core.types import SignalAction
from zksato_strategy.indicators import (
    atr,
    bollinger_bands,
    ema_series,
    highest,
    macd_series,
    rate_of_change,
    rsi,
    sma_series,
    stochastic_oscillator,
    vwap,
    williams_r,
)


@dataclass
class StrategyContext:
    """Context for strategy evaluation."""

    symbol: str
    prices: list[float]
    config: StrategyConfig
    sentiment_score: float | None = None
    candles: list[Candle] | None = None


class StrategyEngine:
    """Deterministic signal generation shared by automation, replay and backtests."""

    def evaluate(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
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

        strategy_map = {
            "ema_cross": self._ema_cross,
            "sma_cross": self._sma_cross,
            "rsi_reversion": self._rsi_reversion,
            "bollinger_reversion": self._bollinger_reversion,
            "momentum": self._momentum,
            "macd_cross": self._macd_cross,
            "breakout": self._breakout,
            "llm_sentiment": self._llm_sentiment,
            "multi_factor": self._multi_factor,
            "scalp": self._scalp,
            "swing": self._swing,
            "position": self._position,
            "vwap": self._vwap,
            "stochastic": self._stochastic,
            "williams_r": self._williams_r_strategy,
            "atr_channel": self._atr_channel,
            "stat_arb": self._stat_arb,
            "tfex_spread": self._tfex_spread,
        }

        if config.name not in strategy_map:
            raise ValueError(f"unknown strategy: {config.name}")

        return strategy_map[config.name](symbol, prices, config, sentiment_score, candles)

    def evaluate_prediction(
        self,
        symbol: str,
        ticks: list[Any],
        min_edge: float = 0.03,
    ) -> Signal:
        """Evaluate prediction market ticks using probability edge."""
        if not ticks:
            return Signal(
                symbol=symbol,
                strategy="prediction_edge",
                action=SignalAction.HOLD,
                price=0.0,
                confidence=0.0,
                reason="no ticks available",
            )

        # Simple probability edge calculation
        up_ticks = sum(1 for t in ticks if getattr(t, "direction", "").upper() == "UP")
        down_ticks = len(ticks) - up_ticks
        total = len(ticks)

        up_prob = up_ticks / total
        down_prob = down_ticks / total

        if up_prob - down_prob > min_edge:
            return Signal(
                symbol=symbol,
                strategy="prediction_edge",
                action=SignalAction.BUY,
                price=float(ticks[-1].price) if hasattr(ticks[-1], "price") else 0.5,
                confidence=up_prob - down_prob,
                reason=f"UP edge: {up_prob:.2%} vs {down_prob:.2%}",
            )
        elif down_prob - up_prob > min_edge:
            return Signal(
                symbol=symbol,
                strategy="prediction_edge",
                action=SignalAction.SELL,
                price=float(ticks[-1].price) if hasattr(ticks[-1], "price") else 0.5,
                confidence=down_prob - up_prob,
                reason=f"DOWN edge: {down_prob:.2%} vs {up_prob:.2%}",
            )

        return Signal(
            symbol=symbol,
            strategy="prediction_edge",
            action=SignalAction.HOLD,
            price=float(ticks[-1].price) if hasattr(ticks[-1], "price") else 0.5,
            confidence=0.0,
            reason=f"no significant edge: UP={up_prob:.2%}, DOWN={down_prob:.2%}",
        )

    # Strategy implementations
    def _ema_cross(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        fast_period = config.parameters.get("fast_period", 9)
        slow_period = config.parameters.get("slow_period", 21)

        fast_ema = ema_series(prices, fast_period)
        slow_ema = ema_series(prices, slow_period)

        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient EMA data",
            )

        current_fast = fast_ema[-1]
        current_slow = slow_ema[-1]
        prev_fast = fast_ema[-2]
        prev_slow = slow_ema[-2]

        price = prices[-1]

        if prev_fast <= prev_slow and current_fast > current_slow:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.7,
                reason="EMA golden cross",
            )
        elif prev_fast >= prev_slow and current_fast < current_slow:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.7,
                reason="EMA death cross",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="no EMA cross",
        )

    def _sma_cross(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        fast_period = config.parameters.get("fast_period", 10)
        slow_period = config.parameters.get("slow_period", 30)

        fast_sma = sma_series(prices, fast_period)
        slow_sma = sma_series(prices, slow_period)

        if len(fast_sma) < 2 or len(slow_sma) < 2:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient SMA data",
            )

        price = prices[-1]

        if fast_sma[-2] <= slow_sma[-2] and fast_sma[-1] > slow_sma[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.65,
                reason="SMA golden cross",
            )
        elif fast_sma[-2] >= slow_sma[-2] and fast_sma[-1] < slow_sma[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.65,
                reason="SMA death cross",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="no SMA cross",
        )

    def _rsi_reversion(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        period = config.parameters.get("period", 14)
        oversold = config.parameters.get("oversold", 30)
        overbought = config.parameters.get("overbought", 70)

        rsi_values = rsi(prices, period)

        if not rsi_values:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient RSI data",
            )

        current_rsi = rsi_values[-1]
        price = prices[-1]

        if current_rsi <= oversold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.75,
                reason=f"RSI oversold: {current_rsi:.1f}",
            )
        elif current_rsi >= overbought:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.75,
                reason=f"RSI overbought: {current_rsi:.1f}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason=f"RSI neutral: {current_rsi:.1f}",
        )

    def _bollinger_reversion(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        period = config.parameters.get("period", 20)
        std_dev = config.parameters.get("std_dev", 2.0)

        upper, _middle, lower = bollinger_bands(prices, period, std_dev)

        if not upper or not lower:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient Bollinger data",
            )

        price = prices[-1]

        if price <= lower[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.7,
                reason="price at lower Bollinger band",
            )
        elif price >= upper[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.7,
                reason="price at upper Bollinger band",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="price within Bollinger bands",
        )

    def _momentum(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        period = config.parameters.get("period", 10)
        threshold = config.parameters.get("threshold", 0.02)

        if len(prices) < period + 1:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient data for momentum",
            )

        roc = rate_of_change(prices, period)
        if not roc:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="no ROC data",
            )

        current_roc = roc[-1]
        price = prices[-1]

        if current_roc > threshold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=min(0.8, current_roc * 10),
                reason=f"positive momentum: {current_roc:.2%}",
            )
        elif current_roc < -threshold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=min(0.8, abs(current_roc) * 10),
                reason=f"negative momentum: {current_roc:.2%}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="momentum neutral",
        )

    def _macd_cross(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        fast = config.parameters.get("fast", 12)
        slow = config.parameters.get("slow", 26)
        signal_period = config.parameters.get("signal", 9)

        macd, signal, _histogram = macd_series(prices, fast, slow, signal_period)

        if len(macd) < 2:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient MACD data",
            )

        price = prices[-1]

        if macd[-2] <= signal[-2] and macd[-1] > signal[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.7,
                reason="MACD bullish cross",
            )
        elif macd[-2] >= signal[-2] and macd[-1] < signal[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.7,
                reason="MACD bearish cross",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="no MACD cross",
        )

    def _breakout(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        period = config.parameters.get("period", 20)

        if len(prices) < period:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient data for breakout",
            )

        high = highest(prices[-period:])
        low = min(prices[-period:])
        price = prices[-1]

        if price >= high:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.75,
                reason=f"breakout above {period}-period high",
            )
        elif price <= low:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.75,
                reason=f"breakdown below {period}-period low",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="no breakout",
        )

    def _llm_sentiment(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        if sentiment_score is None:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="no sentiment score provided",
            )

        threshold = config.parameters.get("threshold", 0.3)
        price = prices[-1]

        if sentiment_score > threshold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=sentiment_score,
                reason=f"positive sentiment: {sentiment_score:.2f}",
            )
        elif sentiment_score < -threshold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=abs(sentiment_score),
                reason=f"negative sentiment: {sentiment_score:.2f}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="sentiment neutral",
        )

    def _multi_factor(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        # Combine multiple factors
        signals = []
        weights = []

        # RSI factor
        rsi_sig = self._rsi_reversion(symbol, prices, config, sentiment_score, candles)
        signals.append(
            1
            if rsi_sig.action == SignalAction.BUY
            else -1
            if rsi_sig.action == SignalAction.SELL
            else 0
        )
        weights.append(config.parameters.get("rsi_weight", 0.3))

        # Momentum factor
        mom_sig = self._momentum(symbol, prices, config, sentiment_score, candles)
        signals.append(
            1
            if mom_sig.action == SignalAction.BUY
            else -1
            if mom_sig.action == SignalAction.SELL
            else 0
        )
        weights.append(config.parameters.get("momentum_weight", 0.3))

        # MACD factor
        macd_sig = self._macd_cross(symbol, prices, config, sentiment_score, candles)
        signals.append(
            1
            if macd_sig.action == SignalAction.BUY
            else -1
            if macd_sig.action == SignalAction.SELL
            else 0
        )
        weights.append(config.parameters.get("macd_weight", 0.2))

        # Sentiment factor
        if sentiment_score is not None:
            signals.append(1 if sentiment_score > 0.2 else -1 if sentiment_score < -0.2 else 0)
            weights.append(config.parameters.get("sentiment_weight", 0.2))

        weighted_sum = sum(s * w for s, w in zip(signals, weights, strict=False))
        total_weight = sum(weights)
        score = weighted_sum / total_weight if total_weight > 0 else 0

        price = prices[-1]

        if score > 0.3:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=min(0.9, score),
                reason=f"multi-factor BUY: {score:.2f}",
            )
        elif score < -0.3:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=min(0.9, abs(score)),
                reason=f"multi-factor SELL: {score:.2f}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason=f"multi-factor neutral: {score:.2f}",
        )

    def _scalp(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        fast = config.parameters.get("fast", 3)
        slow = config.parameters.get("slow", 8)

        fast_ema = ema_series(prices, fast)
        slow_ema = ema_series(prices, slow)

        if len(fast_ema) < 2 or len(slow_ema) < 2:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient EMA data",
            )

        price = prices[-1]

        if fast_ema[-2] <= slow_ema[-2] and fast_ema[-1] > slow_ema[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.6,
                reason="scalp EMA cross up",
            )
        elif fast_ema[-2] >= slow_ema[-2] and fast_ema[-1] < slow_ema[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.6,
                reason="scalp EMA cross down",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="no scalp signal",
        )

    def _swing(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        rsi_period = config.parameters.get("rsi_period", 14)
        rsi_oversold = config.parameters.get("rsi_oversold", 35)
        rsi_overbought = config.parameters.get("rsi_overbought", 65)

        rsi_values = rsi(prices, rsi_period)
        if not rsi_values:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient RSI data",
            )

        # Check trend with SMA
        trend_period = config.parameters.get("trend_period", 50)
        sma_trend = sma_series(prices, trend_period)

        price = prices[-1]
        current_rsi = rsi_values[-1]

        trend_up = len(sma_trend) >= 2 and sma_trend[-1] > sma_trend[-2]
        trend_down = len(sma_trend) >= 2 and sma_trend[-1] < sma_trend[-2]

        if trend_up and current_rsi <= rsi_oversold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.7,
                reason=f"swing buy: uptrend + RSI oversold ({current_rsi:.1f})",
            )
        elif trend_down and current_rsi >= rsi_overbought:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.7,
                reason=f"swing sell: downtrend + RSI overbought ({current_rsi:.1f})",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="no swing signal",
        )

    def _position(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        fast = config.parameters.get("fast", 50)
        slow = config.parameters.get("slow", 200)

        fast_sma = sma_series(prices, fast)
        slow_sma = sma_series(prices, slow)

        if len(fast_sma) < 2 or len(slow_sma) < 2:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient SMA data",
            )

        price = prices[-1]

        if fast_sma[-2] <= slow_sma[-2] and fast_sma[-1] > slow_sma[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.8,
                reason="position: golden cross (50/200)",
            )
        elif fast_sma[-2] >= slow_sma[-2] and fast_sma[-1] < slow_sma[-1]:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.8,
                reason="position: death cross (50/200)",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="no position signal",
        )

    def _vwap(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        if not candles or len(candles) < 2:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="need candles for VWAP",
            )

        vwap_values = vwap(candles)
        if not vwap_values:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="no VWAP data",
            )

        price = prices[-1]
        current_vwap = vwap_values[-1]

        deviation = (price - current_vwap) / current_vwap
        threshold = config.parameters.get("deviation_threshold", 0.01)

        if deviation < -threshold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=min(0.8, abs(deviation) * 50),
                reason=f"price below VWAP: {deviation:.2%}",
            )
        elif deviation > threshold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=min(0.8, deviation * 50),
                reason=f"price above VWAP: {deviation:.2%}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="price near VWAP",
        )

    def _stochastic(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        if not candles or len(candles) < 14:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="need candles for Stochastic",
            )

        k_period = config.parameters.get("k_period", 14)
        d_period = config.parameters.get("d_period", 3)
        oversold = config.parameters.get("oversold", 20)
        overbought = config.parameters.get("overbought", 80)

        k_values, d_values = stochastic_oscillator(candles, k_period, d_period)

        if not k_values or not d_values:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="no Stochastic data",
            )

        price = prices[-1]
        k = k_values[-1]
        d = d_values[-1]

        if k <= oversold and d <= oversold and k > d:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.7,
                reason=f"Stochastic oversold crossover: %K={k:.1f}, %D={d:.1f}",
            )
        elif k >= overbought and d >= overbought and k < d:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.7,
                reason=f"Stochastic overbought crossover: %K={k:.1f}, %D={d:.1f}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="Stochastic neutral",
        )

    def _williams_r_strategy(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        if not candles or len(candles) < 14:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="need candles for Williams %R",
            )

        period = config.parameters.get("period", 14)
        oversold = config.parameters.get("oversold", -80)
        overbought = config.parameters.get("overbought", -20)

        wr_values = williams_r(candles, period)

        if not wr_values:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="no Williams %R data",
            )

        price = prices[-1]
        wr = wr_values[-1]

        if wr <= oversold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.7,
                reason=f"Williams %R oversold: {wr:.1f}",
            )
        elif wr >= overbought:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.7,
                reason=f"Williams %R overbought: {wr:.1f}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="Williams %R neutral",
        )

    def _atr_channel(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        if not candles or len(candles) < 20:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="need candles for ATR channel",
            )

        period = config.parameters.get("period", 14)
        multiplier = config.parameters.get("multiplier", 2.0)

        atr_values = atr(candles, period)
        if not atr_values:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="no ATR data",
            )

        price = prices[-1]
        current_atr = atr_values[-1]

        # Calculate channel around SMA
        sma_values = sma_series(prices, period)
        if not sma_values:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=price,
                confidence=0.0,
                reason="no SMA for channel",
            )

        sma = sma_values[-1]
        upper = sma + multiplier * current_atr
        lower = sma - multiplier * current_atr

        if price <= lower:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=0.7,
                reason=f"price at lower ATR channel: {price:.2f} <= {lower:.2f}",
            )
        elif price >= upper:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=0.7,
                reason=f"price at upper ATR channel: {price:.2f} >= {upper:.2f}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason="price within ATR channel",
        )

    def _stat_arb(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        # Placeholder for statistical arbitrage
        lookback = config.parameters.get("lookback", 100)
        z_threshold = config.parameters.get("z_threshold", 2.0)

        if len(prices) < lookback:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="insufficient data for stat arb",
            )

        # Simple z-score mean reversion
        recent = prices[-lookback:]
        mean = sum(recent) / len(recent)
        std = (sum((p - mean) ** 2 for p in recent) / len(recent)) ** 0.5

        if std == 0:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.HOLD,
                price=prices[-1],
                confidence=0.0,
                reason="zero variance",
            )

        z_score = (prices[-1] - mean) / std
        price = prices[-1]

        if z_score <= -z_threshold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.BUY,
                price=price,
                confidence=min(0.9, abs(z_score) / 4),
                reason=f"stat arb: z-score {z_score:.2f}",
            )
        elif z_score >= z_threshold:
            return Signal(
                symbol=symbol,
                strategy=config.name,
                action=SignalAction.SELL,
                price=price,
                confidence=min(0.9, z_score / 4),
                reason=f"stat arb: z-score {z_score:.2f}",
            )

        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=price,
            confidence=0.0,
            reason=f"stat arb: z-score {z_score:.2f}",
        )

    def _tfex_spread(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None = None,
        candles: list[Candle] | None = None,
    ) -> Signal:
        # Placeholder for TFEX spread trading
        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=SignalAction.HOLD,
            price=prices[-1],
            confidence=0.0,
            reason="TFEX spread strategy not implemented",
        )
