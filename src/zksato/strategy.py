from __future__ import annotations

from zksato.domain import Candle, Signal, SignalAction, StrategyConfig
from zksato.indicators import bollinger_bands, ema, highest, macd, rate_of_change, rsi, sma, vwap
from zksato.prediction.strategy import ProbabilityEdgeStrategy


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
        if config.name == "multi_factor":
            return self._multi_factor(symbol, prices, config, sentiment_score)
        if config.name == "scalp":
            return self._scalp(symbol, prices, config)
        if config.name == "swing":
            return self._swing(symbol, prices, config)
        if config.name == "position":
            return self._position(symbol, prices, config)
        if config.name == "vwap":
            return self._vwap(symbol, prices, config, candles)

        raise ValueError(f"unknown strategy: {config.name}")

    def evaluate_prediction(
        self,
        symbol: str,
        ticks: list,
        min_edge: float = 0.03,
    ) -> Signal:
        """Evaluate prediction market ticks using ProbabilityEdgeStrategy.

        Returns a Signal with BUY for UP, SELL for DOWN, or HOLD if no edge.
        """
        if not ticks:
            return Signal(
                symbol=symbol,
                strategy="prediction_edge",
                action=SignalAction.HOLD,
                price=0.0,
                confidence=0.0,
                reason="no ticks provided",
            )
        latest = ticks[-1]
        model = ProbabilityEdgeStrategy(min_edge=min_edge)
        pred_signal = model.signal(latest)
        if pred_signal is None:
            return Signal(
                symbol=symbol,
                strategy="prediction_edge",
                action=SignalAction.HOLD,
                price=latest.spot,
                confidence=0.0,
                reason="model edge below minimum threshold",
            )
        action = SignalAction.BUY if pred_signal.side == "up" else SignalAction.SELL
        return Signal(
            symbol=symbol,
            strategy="prediction_edge",
            action=action,
            price=latest.spot,
            confidence=max(0.0, min(1.0, pred_signal.probability)),
            reason=f"probability={pred_signal.probability:.3f}, edge={pred_signal.edge:.3f}",
        )

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

    def _multi_factor(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None,
    ) -> Signal:
        ema_sig = self._ema_cross(symbol, prices, config)
        rsi_sig = self._rsi_reversion(symbol, prices, config)
        llm_sig = (
            self._llm_sentiment(symbol, prices, config, sentiment_score)
            if sentiment_score
            else None
        )

        score = 0.0
        if ema_sig.action == SignalAction.BUY:
            score += 1
        elif ema_sig.action == SignalAction.SELL:
            score -= 1

        if rsi_sig.action == SignalAction.BUY:
            score += 1
        elif rsi_sig.action == SignalAction.SELL:
            score -= 1

        if llm_sig:
            if llm_sig.action == SignalAction.BUY:
                score += 1.5
            elif llm_sig.action == SignalAction.SELL:
                score -= 1.5

        price = prices[-1]
        if score >= 2.0:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                min(score / 3.5, 1.0),
                f"Bullish (score: {score})",
            )
        if score <= -2.0:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                min(abs(score) / 3.5, 1.0),
                f"Bearish (score: {score})",
            )

        return self._signal(
            symbol, config, price, SignalAction.HOLD, 0.0, f"Mixed (score: {score})"
        )

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
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        sentiment_score: float | None,
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

    def _scalp(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        """Fast EMA crossover with Bollinger Band confirmation."""
        fast = ema(prices, config.scalp_fast_period)
        slow = ema(prices, config.scalp_slow_period)
        prev_fast = ema(prices[:-1], config.scalp_fast_period)
        prev_slow = ema(prices[:-1], config.scalp_slow_period)
        price = prices[-1]
        if fast is None or slow is None or prev_fast is None or prev_slow is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient scalp EMA history"
            )
        bands = bollinger_bands(prices, period=20, deviations=2.0)
        if bands is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient Bollinger history"
            )
        _, _, upper = bands
        _, _, lower = bands
        band_width = upper - lower
        near_upper = price >= upper - band_width * 0.1
        near_lower = price <= lower + band_width * 0.1
        if prev_fast <= prev_slow and fast > slow and near_upper:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                0.7 + abs(fast - slow) / price * 10,
                f"scalp EMA{config.scalp_fast_period}/"
                f"{config.scalp_slow_period} bullish near upper band",
            )
        if prev_fast >= prev_slow and fast < slow and near_lower:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                0.7 + abs(fast - slow) / price * 10,
                f"scalp EMA{config.scalp_fast_period}/"
                f"{config.scalp_slow_period} bearish near lower band",
            )
        return self._signal(
            symbol, config, price, SignalAction.HOLD, 0.25, "scalp no confirmed crossover near band"
        )

    def _swing(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        """MACD cross combined with RSI reversion."""
        macd_sig = self._macd_cross(symbol, prices, config)
        rsi_value = rsi(prices, config.swing_rsi_period)
        price = prices[-1]
        if rsi_value is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient swing RSI history"
            )
        if macd_sig.action == SignalAction.BUY and rsi_value < 35:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                0.5 + (35 - rsi_value) / 35 * 0.2,
                f"swing MACD bullish + RSI {rsi_value:.1f} < 35",
            )
        if macd_sig.action == SignalAction.SELL and rsi_value > 65:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                0.5 + (rsi_value - 65) / 35 * 0.2,
                f"swing MACD bearish + RSI {rsi_value:.1f} > 65",
            )
        return self._signal(
            symbol,
            config,
            price,
            SignalAction.HOLD,
            0.25,
            f"swing MACD {macd_sig.action.value} without RSI confirmation ({rsi_value:.1f})",
        )

    def _position(self, symbol: str, prices: list[float], config: StrategyConfig) -> Signal:
        """Long-term SMA crossover for high-conviction position signals."""
        fast = sma(prices, config.position_fast_period)
        slow = sma(prices, config.position_slow_period)
        prev_fast = sma(prices[:-1], config.position_fast_period)
        prev_slow = sma(prices[:-1], config.position_slow_period)
        price = prices[-1]
        if fast is None or slow is None or prev_fast is None or prev_slow is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "insufficient position SMA history"
            )
        crossover_gap = abs(fast - slow) / price
        if prev_fast <= prev_slow and fast > slow and crossover_gap >= 0.02:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                0.3 + crossover_gap * 10,
                f"position SMA{config.position_fast_period}/"
                f"{config.position_slow_period} bullish crossover",
            )
        if prev_fast >= prev_slow and fast < slow and crossover_gap >= 0.02:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                0.3 + crossover_gap * 10,
                f"position SMA{config.position_fast_period}/"
                f"{config.position_slow_period} bearish crossover",
            )
        return self._signal(
            symbol, config, price, SignalAction.HOLD, 0.25, "no significant position crossover"
        )

    def _vwap(
        self,
        symbol: str,
        prices: list[float],
        config: StrategyConfig,
        candles: list[Candle] | None,
    ) -> Signal:
        """VWAP-based dynamic support/resistance strategy."""
        price = prices[-1]
        if candles is None or len(candles) < config.vwap_period:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.HOLD,
                0.0,
                "insufficient candle history for VWAP",
            )
        vwap_value = vwap(candles, period=config.vwap_period)
        if vwap_value is None:
            return self._signal(
                symbol, config, price, SignalAction.HOLD, 0.0, "unable to compute VWAP"
            )
        distance_pct = (price - vwap_value) / vwap_value if vwap_value > 0 else 0.0
        prev_price = prices[-2] if len(prices) >= 2 else price
        prev_distance_pct = (prev_price - vwap_value) / vwap_value if vwap_value > 0 else 0.0
        if prev_distance_pct > 0 and distance_pct >= -0.005 and distance_pct <= 0.02:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.BUY,
                0.5 + max(0.0, -distance_pct) * 20,
                f"price pulled back to VWAP {vwap_value:.2f} from above",
            )
        if prev_distance_pct < 0 and distance_pct < -0.01:
            return self._signal(
                symbol,
                config,
                price,
                SignalAction.SELL,
                0.5 + abs(distance_pct) * 20,
                f"price dropped below VWAP {vwap_value:.2f}",
            )
        return self._signal(
            symbol,
            config,
            price,
            SignalAction.HOLD,
            0.25,
            f"VWAP {vwap_value:.2f} neutral (distance {distance_pct:.2%})",
        )
