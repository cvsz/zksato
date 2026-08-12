from __future__ import annotations

from zksato.domain import Signal, SignalAction, StrategyConfig
from zksato.indicators import bollinger_bands, ema, highest, macd, rate_of_change, rsi, sma


class StrategyEngine:
    """Deterministic signal generation shared by automation, replay and backtests."""

    def evaluate(self, symbol: str, prices: list[float], config: StrategyConfig, sentiment_score: float | None = None) -> Signal:
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
        if config.name == "sma_cross":
            return self._sma_cross(symbol, prices, config)
        if config.name == "rsi_reversion":
            return self._rsi_reversion(symbol, prices, config)
        if config.name == "bollinger_reversion":
            return self._bollinger_reversion(symbol, prices, config)
        if config.name == "momentum":
            return self._momentum(symbol, prices, config)
        if config.name == "macd_cross":
            return self._macd_cross(symbol, prices, config)
        if config.name == "breakout":
            return self._breakout(symbol, prices, config)
        if config.name == "llm_sentiment":
            return self._llm_sentiment(symbol, prices, config, sentiment_score)

        raise ValueError(f"unknown strategy: {config.name}")

    @staticmethod
    def _signal(
        symbol: str,
        config: StrategyConfig,
        price: float,
        action: SignalAction,
        confidence: float,
        reason: str,
    ) -> Signal:
        return Signal(
            symbol=symbol,
            strategy=config.name,
            action=action,
            price=price,
            confidence=max(0.0, min(confidence, 1.0)),
            reason=reason,
        )

    def _ema_cross(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        fast = ema(prices, config.fast_period)
        slow = ema(prices, config.slow_period)
        prev_fast = ema(prices[:-1], config.fast_period)
        prev_slow = ema(prices[:-1], config.slow_period)
        price = prices[-1]
        if fast is None or slow is None or prev_fast is None or prev_slow is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient EMA history"
            )
        if prev_fast <= prev_slow and fast > slow:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                abs(fast - slow) / price * 20,
                f"EMA{config.fast_period} crossed above EMA{config.slow_period}",
            )
        if prev_fast >= prev_slow and fast < slow:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                abs(fast - slow) / price * 20,
                f"EMA{config.fast_period} crossed below EMA{config.slow_period}",
            )
        return self._signal(symbol, config, price, SignalAction.HOLD, 0.25, "no EMA crossover")

    def _sma_cross(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        fast = sma(prices, config.fast_period)
        slow = sma(prices, config.slow_period)
        prev_fast = sma(prices[:-1], config.fast_period)
        prev_slow = sma(prices[:-1], config.slow_period)
        price = prices[-1]
        if fast is None or slow is None or prev_fast is None or prev_slow is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient SMA history"
            )
        if prev_fast <= prev_slow and fast > slow:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                abs(fast - slow) / price * 20,
                f"SMA{config.fast_period} crossed above SMA{config.slow_period}",
            )
        if prev_fast >= prev_slow and fast < slow:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                abs(fast - slow) / price * 20,
                f"SMA{config.fast_period} crossed below SMA{config.slow_period}",
            )
        return self._signal(symbol, config, price, SignalAction.HOLD, 0.25, "no SMA crossover")

    def _rsi_reversion(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        value = rsi(prices, config.rsi_period)
        price = prices[-1]
        if value is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient RSI history"
            )
        if value <= config.rsi_buy:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                (config.rsi_buy - value + 10) / 30,
                f"RSI {value:.1f} <= {config.rsi_buy:.1f}",
            )
        if value >= config.rsi_sell:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                (value - config.rsi_sell + 10) / 30,
                f"RSI {value:.1f} >= {config.rsi_sell:.1f}",
            )
        return self._signal(
            symbol, config, price, SignalAction.HOLD, 0.25, f"RSI neutral at {value:.1f}"
        )

    def _bollinger_reversion(
        self, symbol: str, prices: list[float], config: StrategyConfig
    ) -> Signal:
        price = prices[-1]
        bands = bollinger_bands(
            prices,
            period=config.bollinger_period,
            deviations=config.bollinger_deviations,
        )
        if bands is None:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.HOLD,
                0.0,
                "insufficient Bollinger history",
            )
        lower, middle, upper = bands
        width = max(upper - lower, price * 1e-9)
        if price <= lower:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                0.5 + ((lower - price) / width) * 4,
                f"price {price:.2f} <= lower Bollinger band {lower:.2f}",
            )
        if price >= upper:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                0.5 + ((price - upper) / width) * 4,
                f"price {price:.2f} >= upper Bollinger band {upper:.2f}",
            )
        return self._signal(
            symbol,
            config,
            price,
            SignalAction.HOLD,
            0.25,
            f"inside Bollinger bands around {middle:.2f}",
        )

    def _momentum(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        price = prices[-1]
        roc = rate_of_change(prices, config.momentum_period)
        if roc is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient momentum history"
            )
        threshold = config.momentum_threshold_pct
        if roc >= threshold:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                0.5 + abs(roc - threshold) / max(threshold or 1.0, 1.0) * 0.25,
                f"{config.momentum_period}-period momentum {roc:.2f}% >= {threshold:.2f}%",
            )
        if roc <= -threshold:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                0.5 + abs(roc + threshold) / max(threshold or 1.0, 1.0) * 0.25,
                f"{config.momentum_period}-period momentum {roc:.2f}% <= {-threshold:.2f}%",
            )
        return self._signal(
            symbol,
            config,
            price,
            SignalAction.HOLD,
            0.25,
            f"momentum neutral at {roc:.2f}%",
        )

    def _macd_cross(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        current = macd(prices, config.fast_period, config.slow_period, config.signal_period)
        previous = macd(prices[:-1], config.fast_period, config.slow_period, config.signal_period)
        price = prices[-1]
        if current is None or previous is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient MACD history"
            )
        line, signal_line, histogram = current
        prev_line, prev_signal, _ = previous
        if prev_line <= prev_signal and line > signal_line:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                0.5 + abs(histogram) / price * 20,
                "MACD crossed above signal line",
            )
        if prev_line >= prev_signal and line < signal_line:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                0.5 + abs(histogram) / price * 20,
                "MACD crossed below signal line",
            )
        return self._signal(
            symbol,
            config,
            price,
            SignalAction.HOLD,
            0.25,
            f"MACD histogram {histogram:.4f} without crossover",
        )

    def _breakout(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        price = prices[-1]
        previous = prices[:-1]
        upper = highest(previous, config.breakout_period)
        if upper is None:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.HOLD,
                0.0,
                "insufficient breakout history",
            )
        if price > upper:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                ((price - upper) / upper) * 20 + 0.5,
                f"price broke above {config.breakout_period}-period high {upper:.2f}",
            )
        return self._signal(
            symbol,
            config,
            price,
            SignalAction.HOLD,
            0.25,
            f"below breakout level {upper:.2f}",
        )


    def _llm_sentiment(
        self, symbol: str, prices: list[float], config: StrategyConfig, sentiment_score: float | None
    ) -> Signal:
        price = prices[-1]
        score = sentiment_score if sentiment_score is not None else 0.5
        if score >= config.sentiment_buy_threshold:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                score,
                f"LLM sentiment {score:.2f} >= {config.sentiment_buy_threshold:.2f}",
            )
        if score <= config.sentiment_sell_threshold:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                1.0 - score,
                f"LLM sentiment {score:.2f} <= {config.sentiment_sell_threshold:.2f}",
            )
        return self._signal(
            symbol, config, price, SignalAction.HOLD, 0.5, f"LLM sentiment neutral at {score:.2f}"
        )
