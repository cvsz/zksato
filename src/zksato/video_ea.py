from __future__ import annotations

from enum import StrEnum
from math import floor

from pydantic import BaseModel, Field, model_validator

from zksato.domain import Candle, Side
from zksato.indicators import atr


class VideoEaBias(StrEnum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class VideoEaGridMode(StrEnum):
    PA_FILTERED = "pa_filtered"
    SYMMETRIC_RESEARCH = "symmetric_research"


class VideoEaMarketProfile(StrEnum):
    SET_EQUITY = "set_equity"
    TFEX_RESEARCH = "tfex_research"
    GENERIC_RESEARCH = "generic_research"


class VideoEaZone(BaseModel):
    kind: str = Field(pattern="^(support|resistance)$")
    level: float = Field(gt=0)
    low: float = Field(gt=0)
    high: float = Field(gt=0)
    source_index: int = Field(ge=0)
    breakout_index: int | None = Field(default=None, ge=0)
    retest_index: int | None = Field(default=None, ge=0)


class VideoEaTrigger(BaseModel):
    side: Side
    level: int = Field(ge=1)
    trigger_price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    dedupe_key: str = Field(min_length=1, max_length=160)
    virtual: bool = True


class VideoEaConfig(BaseModel):
    """Bounded, research-first interpretation of the supplied trading videos."""

    grid_mode: VideoEaGridMode = VideoEaGridMode.PA_FILTERED
    market_profile: VideoEaMarketProfile = VideoEaMarketProfile.SET_EQUITY
    lookback_bars: int = Field(default=48, ge=12, le=500)
    pivot_window: int = Field(default=2, ge=1, le=10)
    atr_period: int = Field(default=14, ge=2, le=100)
    breakout_buffer_atr: float = Field(default=0.10, ge=0, le=3)
    retest_tolerance_atr: float = Field(default=0.35, gt=0, le=5)
    zone_half_width_atr: float = Field(default=0.20, gt=0, le=3)
    rejection_wick_ratio: float = Field(default=0.50, ge=0, le=10)
    grid_step_atr: float = Field(default=0.35, gt=0, le=10)
    grid_step_abs: float | None = Field(default=None, gt=0)
    tick_size: float = Field(default=0.01, gt=0)
    levels_per_side: int = Field(default=6, ge=1, le=20)
    quantity_per_level: int = Field(default=1, ge=1)
    max_total_quantity: int = Field(default=12, ge=1)
    max_pending_triggers: int = Field(default=12, ge=1, le=40)
    basket_take_profit_r: float = Field(default=1.50, gt=0, le=20)
    cycle_stop_r: float = Field(default=1.00, gt=0, le=20)
    cooldown_bars: int = Field(default=2, ge=0, le=100)
    require_pa_confirmation: bool = True

    @model_validator(mode="after")
    def validate_caps(self) -> VideoEaConfig:
        if self.quantity_per_level > self.max_total_quantity:
            raise ValueError("quantity_per_level cannot exceed max_total_quantity")
        return self


class VideoEaPlanRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    candles: list[Candle] = Field(min_length=8, max_length=5000)
    config: VideoEaConfig = Field(default_factory=VideoEaConfig)
    research_only: bool = True


class VideoEaPlan(BaseModel):
    symbol: str
    bias: VideoEaBias
    anchor_price: float
    atr: float
    grid_step: float
    zone: VideoEaZone | None = None
    triggers: list[VideoEaTrigger] = Field(default_factory=list)
    invalidation_price: float | None = None
    basket_take_profit_r: float
    cycle_stop_r: float
    max_total_quantity: int
    research_only: bool = True
    executable: bool = False
    reasons: list[str] = Field(default_factory=list)


class VideoEaActivationRequest(BaseModel):
    plan: VideoEaPlan
    previous_price: float = Field(gt=0)
    current_price: float = Field(gt=0)


class VideoEaActivationResult(BaseModel):
    symbol: str
    triggered: list[VideoEaTrigger] = Field(default_factory=list)
    executable: bool = False
    reason: str = "virtual trigger evaluation only"


class VideoDerivedEaPlanner:
    """Pure planner: no broker, credential, order-submission, or live authority."""

    def plan(self, request: VideoEaPlanRequest) -> VideoEaPlan:
        symbol = request.symbol.strip().upper()
        config = request.config
        candles = request.candles[-config.lookback_bars :]
        minimum = max(config.atr_period + 2, config.pivot_window * 2 + 5)
        if len(candles) < minimum:
            return self._empty_plan(
                symbol,
                candles[-1].close,
                config,
                "insufficient candle history for PA-zone and ATR planning",
            )

        atr_value = atr(candles, config.atr_period)
        if atr_value is None or atr_value <= 0:
            return self._empty_plan(
                symbol,
                candles[-1].close,
                config,
                "ATR unavailable; planner fails closed",
            )

        bias, zone, reasons = self._detect_pa_structure(candles, atr_value, config)
        anchor = candles[-1].close
        raw_step = config.grid_step_abs or (atr_value * config.grid_step_atr)
        step = max(config.tick_size, self._round_to_tick(raw_step, config.tick_size))

        blocked = self._blocked_reason(request, bias)
        if blocked:
            return self._base_plan(
                symbol,
                bias,
                anchor,
                atr_value,
                step,
                zone,
                config,
                reasons + [blocked],
            )
        if config.grid_mode == VideoEaGridMode.PA_FILTERED and bias == VideoEaBias.NEUTRAL:
            return self._base_plan(
                symbol,
                bias,
                anchor,
                atr_value,
                step,
                zone,
                config,
                reasons + ["PA-filtered mode requires directional evidence"],
            )

        sides = self._sides(config, bias)
        max_by_quantity = config.max_total_quantity // config.quantity_per_level
        levels = min(
            config.levels_per_side,
            max_by_quantity // len(sides),
            config.max_pending_triggers // len(sides),
        )
        triggers = self._triggers(symbol, anchor, step, sides, levels, config)
        if levels < config.levels_per_side:
            reasons.append("ladder truncated by hard quantity/pending-trigger caps")
        reasons.append("fixed-size only; martingale and duplicate stacking are absent")
        invalidation = self._invalidation(anchor, atr_value, step, bias, zone, config)
        return VideoEaPlan(
            symbol=symbol,
            bias=bias,
            anchor_price=anchor,
            atr=atr_value,
            grid_step=step,
            zone=zone,
            triggers=triggers,
            invalidation_price=invalidation,
            basket_take_profit_r=config.basket_take_profit_r,
            cycle_stop_r=config.cycle_stop_r,
            max_total_quantity=config.max_total_quantity,
            research_only=True,
            executable=False,
            reasons=reasons,
        )

    @staticmethod
    def activate(request: VideoEaActivationRequest) -> VideoEaActivationResult:
        fresh: list[VideoEaTrigger] = []
        for trigger in request.plan.triggers:
            up = (
                trigger.side == Side.BUY
                and request.previous_price < trigger.trigger_price <= request.current_price
            )
            down = (
                trigger.side == Side.SELL
                and request.previous_price > trigger.trigger_price >= request.current_price
            )
            if up or down:
                fresh.append(trigger)
        reason = "no virtual trigger crossed"
        if fresh:
            reason = (
                "virtual crossings detected; rebuild trusted OrderIntent and pass "
                "TradingService/RiskEngine"
            )
        return VideoEaActivationResult(
            symbol=request.plan.symbol,
            triggered=fresh,
            executable=False,
            reason=reason,
        )

    @staticmethod
    def _blocked_reason(request: VideoEaPlanRequest, bias: VideoEaBias) -> str | None:
        config = request.config
        if (
            config.market_profile == VideoEaMarketProfile.SET_EQUITY
            and config.grid_mode == VideoEaGridMode.SYMMETRIC_RESEARCH
        ):
            return "SET-equity profile rejects symmetric long/short grids"
        if (
            config.market_profile == VideoEaMarketProfile.SET_EQUITY
            and config.grid_mode == VideoEaGridMode.PA_FILTERED
            and bias == VideoEaBias.SHORT
        ):
            return "SET-equity bearish evidence is informational/exit-only; no naked short ladder"
        if config.grid_mode == VideoEaGridMode.SYMMETRIC_RESEARCH and not request.research_only:
            return "symmetric grid is research/paper-only"
        return None

    @staticmethod
    def _sides(config: VideoEaConfig, bias: VideoEaBias) -> list[Side]:
        if config.grid_mode == VideoEaGridMode.SYMMETRIC_RESEARCH:
            return [Side.BUY, Side.SELL]
        return [Side.BUY] if bias == VideoEaBias.LONG else [Side.SELL]

    def _triggers(
        self,
        symbol: str,
        anchor: float,
        step: float,
        sides: list[Side],
        levels: int,
        config: VideoEaConfig,
    ) -> list[VideoEaTrigger]:
        result: list[VideoEaTrigger] = []
        for side in sides:
            direction = 1 if side == Side.BUY else -1
            for level in range(1, levels + 1):
                price = self._round_to_tick(
                    anchor + (direction * step * level),
                    config.tick_size,
                )
                result.append(
                    VideoEaTrigger(
                        side=side,
                        level=level,
                        trigger_price=price,
                        quantity=config.quantity_per_level,
                        dedupe_key=f"video-ea:{symbol}:{side.value}:{level}:{price:.10f}",
                    )
                )
        return result

    def _detect_pa_structure(
        self,
        candles: list[Candle],
        atr_value: float,
        config: VideoEaConfig,
    ) -> tuple[VideoEaBias, VideoEaZone | None, list[str]]:
        highs = self._pivot_highs(candles, config.pivot_window)
        lows = self._pivot_lows(candles, config.pivot_window)
        buffer = atr_value * config.breakout_buffer_atr
        tolerance = atr_value * config.retest_tolerance_atr
        half_width = atr_value * config.zone_half_width_atr
        found: list[tuple[int, VideoEaBias, VideoEaZone, str]] = []

        for index, level in highs:
            match = self._find_retest(
                candles,
                index,
                level,
                buffer,
                tolerance,
                bullish=True,
                config=config,
            )
            if match:
                breakout_index, retest_index = match
                found.append(
                    (
                        retest_index,
                        VideoEaBias.LONG,
                        self._zone(
                            "support",
                            level,
                            half_width,
                            index,
                            breakout_index,
                            retest_index,
                            config,
                        ),
                        "bullish breakout-retest / resistance-to-support flip detected",
                    )
                )

        for index, level in lows:
            match = self._find_retest(
                candles,
                index,
                level,
                buffer,
                tolerance,
                bullish=False,
                config=config,
            )
            if match:
                breakout_index, retest_index = match
                found.append(
                    (
                        retest_index,
                        VideoEaBias.SHORT,
                        self._zone(
                            "resistance",
                            level,
                            half_width,
                            index,
                            breakout_index,
                            retest_index,
                            config,
                        ),
                        "bearish breakout-retest / support-to-resistance flip detected",
                    )
                )

        if found:
            _, bias, zone, reason = max(found, key=lambda item: item[0])
            return bias, zone, [reason]
        return self._direct_rejection(candles, highs, lows, tolerance, half_width, config)

    def _find_retest(
        self,
        candles: list[Candle],
        pivot_index: int,
        level: float,
        buffer: float,
        tolerance: float,
        *,
        bullish: bool,
        config: VideoEaConfig,
    ) -> tuple[int, int] | None:
        for breakout in range(pivot_index + 1, len(candles) - 1):
            close = candles[breakout].close
            if bullish and close <= level + buffer:
                continue
            if not bullish and close >= level - buffer:
                continue
            for retest in range(breakout + 1, len(candles)):
                candle = candles[retest]
                if bullish:
                    touched = candle.low <= level + tolerance
                    held = candle.close >= level - tolerance
                    confirmed = self._bullish_pa(candles, retest, config.rejection_wick_ratio)
                else:
                    touched = candle.high >= level - tolerance
                    held = candle.close <= level + tolerance
                    confirmed = self._bearish_pa(candles, retest, config.rejection_wick_ratio)
                if not config.require_pa_confirmation:
                    confirmed = True
                if touched and held and confirmed:
                    return breakout, retest
            break
        return None

    def _direct_rejection(
        self,
        candles: list[Candle],
        highs: list[tuple[int, float]],
        lows: list[tuple[int, float]],
        tolerance: float,
        half_width: float,
        config: VideoEaConfig,
    ) -> tuple[VideoEaBias, VideoEaZone | None, list[str]]:
        last_index = len(candles) - 1
        last = candles[last_index]
        if lows:
            index, level = lows[-1]
            bullish = self._bullish_pa(candles, last_index, config.rejection_wick_ratio)
            if last.low <= level + tolerance and last.close >= level and bullish:
                zone = self._zone(
                    "support", level, half_width, index, None, last_index, config
                )
                return VideoEaBias.LONG, zone, ["bullish PA rejection at support/demand"]
        if highs:
            index, level = highs[-1]
            bearish = self._bearish_pa(candles, last_index, config.rejection_wick_ratio)
            if last.high >= level - tolerance and last.close <= level and bearish:
                zone = self._zone(
                    "resistance", level, half_width, index, None, last_index, config
                )
                return VideoEaBias.SHORT, zone, ["bearish PA rejection at resistance/supply"]
        return VideoEaBias.NEUTRAL, None, ["no confirmed PA rejection or breakout-retest"]

    @staticmethod
    def _zone(
        kind: str,
        level: float,
        half_width: float,
        source_index: int,
        breakout_index: int | None,
        retest_index: int,
        config: VideoEaConfig,
    ) -> VideoEaZone:
        return VideoEaZone(
            kind=kind,
            level=level,
            low=max(config.tick_size, level - half_width),
            high=level + half_width,
            source_index=source_index,
            breakout_index=breakout_index,
            retest_index=retest_index,
        )

    @staticmethod
    def _pivot_highs(candles: list[Candle], window: int) -> list[tuple[int, float]]:
        result: list[tuple[int, float]] = []
        for index in range(window, len(candles) - window):
            value = candles[index].high
            before = candles[index - window : index]
            after = candles[index + 1 : index + window + 1]
            if all(value >= item.high for item in before) and all(
                value > item.high for item in after
            ):
                result.append((index, value))
        return result

    @staticmethod
    def _pivot_lows(candles: list[Candle], window: int) -> list[tuple[int, float]]:
        result: list[tuple[int, float]] = []
        for index in range(window, len(candles) - window):
            value = candles[index].low
            before = candles[index - window : index]
            after = candles[index + 1 : index + window + 1]
            if all(value <= item.low for item in before) and all(
                value < item.low for item in after
            ):
                result.append((index, value))
        return result

    @staticmethod
    def _bullish_pa(candles: list[Candle], index: int, ratio: float) -> bool:
        candle = candles[index]
        body = max(abs(candle.close - candle.open), 1e-12)
        wick = min(candle.open, candle.close) - candle.low
        rejection = candle.close >= candle.open and wick >= body * ratio
        if index == 0:
            return rejection
        previous = candles[index - 1]
        engulfing = (
            previous.close < previous.open
            and candle.close > candle.open
            and candle.close >= previous.open
            and candle.open <= previous.close
        )
        return rejection or engulfing

    @staticmethod
    def _bearish_pa(candles: list[Candle], index: int, ratio: float) -> bool:
        candle = candles[index]
        body = max(abs(candle.close - candle.open), 1e-12)
        wick = candle.high - max(candle.open, candle.close)
        rejection = candle.close <= candle.open and wick >= body * ratio
        if index == 0:
            return rejection
        previous = candles[index - 1]
        engulfing = (
            previous.close > previous.open
            and candle.close < candle.open
            and candle.open >= previous.close
            and candle.close <= previous.open
        )
        return rejection or engulfing

    def _invalidation(
        self,
        anchor: float,
        atr_value: float,
        step: float,
        bias: VideoEaBias,
        zone: VideoEaZone | None,
        config: VideoEaConfig,
    ) -> float | None:
        if zone is None or bias == VideoEaBias.NEUTRAL:
            return None
        distance = max(atr_value * config.cycle_stop_r, step)
        if bias == VideoEaBias.LONG:
            value = min(zone.low - distance, anchor - distance)
        else:
            value = max(zone.high + distance, anchor + distance)
        return self._round_to_tick(value, config.tick_size)

    @staticmethod
    def _empty_plan(
        symbol: str,
        anchor: float,
        config: VideoEaConfig,
        reason: str,
    ) -> VideoEaPlan:
        step = config.grid_step_abs or config.tick_size
        return VideoEaPlan(
            symbol=symbol,
            bias=VideoEaBias.NEUTRAL,
            anchor_price=anchor,
            atr=0.0,
            grid_step=step,
            basket_take_profit_r=config.basket_take_profit_r,
            cycle_stop_r=config.cycle_stop_r,
            max_total_quantity=config.max_total_quantity,
            reasons=[reason],
        )

    @staticmethod
    def _base_plan(
        symbol: str,
        bias: VideoEaBias,
        anchor: float,
        atr_value: float,
        step: float,
        zone: VideoEaZone | None,
        config: VideoEaConfig,
        reasons: list[str],
    ) -> VideoEaPlan:
        return VideoEaPlan(
            symbol=symbol,
            bias=bias,
            anchor_price=anchor,
            atr=atr_value,
            grid_step=step,
            zone=zone,
            basket_take_profit_r=config.basket_take_profit_r,
            cycle_stop_r=config.cycle_stop_r,
            max_total_quantity=config.max_total_quantity,
            reasons=reasons,
        )

    @staticmethod
    def _round_to_tick(value: float, tick_size: float) -> float:
        ticks = floor((value / tick_size) + 0.5)
        return max(tick_size, ticks * tick_size)
