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
    """Safe, instrument-agnostic interpretation of the supplied trading videos.

    The videos show a stop-order ladder on XAUUSD with roughly 0.30 price spacing and
    repeated basket resets. This configuration deliberately bounds the ladder, uses
    fixed sizing only, and keeps symmetric operation research-only.
    """

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
    """Pure planning engine. It never calls a broker or submits an order."""

    def plan(self, request: VideoEaPlanRequest) -> VideoEaPlan:
        symbol = request.symbol.strip().upper()
        config = request.config
        candles = request.candles[-config.lookback_bars :]
        if len(candles) < max(config.atr_period + 2, config.pivot_window * 2 + 5):
            price = request.candles[-1].close
            return VideoEaPlan(
                symbol=symbol,
                bias=VideoEaBias.NEUTRAL,
                anchor_price=price,
                atr=0.0,
                grid_step=config.grid_step_abs or config.tick_size,
                basket_take_profit_r=config.basket_take_profit_r,
                cycle_stop_r=config.cycle_stop_r,
                max_total_quantity=config.max_total_quantity,
                research_only=True,
                executable=False,
                reasons=["insufficient candle history for PA-zone and ATR planning"],
            )

        atr_value = atr(candles, config.atr_period)
        if atr_value is None or atr_value <= 0:
            price = candles[-1].close
            return VideoEaPlan(
                symbol=symbol,
                bias=VideoEaBias.NEUTRAL,
                anchor_price=price,
                atr=0.0,
                grid_step=config.grid_step_abs or config.tick_size,
                basket_take_profit_r=config.basket_take_profit_r,
                cycle_stop_r=config.cycle_stop_r,
                max_total_quantity=config.max_total_quantity,
                research_only=True,
                executable=False,
                reasons=["ATR unavailable; planner fails closed"],
            )

        bias, zone, reasons = self._detect_pa_structure(candles, atr_value, config)
        anchor = candles[-1].close
        step = self._round_to_tick(
            config.grid_step_abs or (atr_value * config.grid_step_atr),
            config.tick_size,
        )
        if step < config.tick_size:
            step = config.tick_size

        if (
            config.market_profile == VideoEaMarketProfile.SET_EQUITY
            and config.grid_mode == VideoEaGridMode.SYMMETRIC_RESEARCH
        ):
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
                research_only=True,
                executable=False,
                reasons=reasons
                + [
                    "SET-equity profile rejects symmetric long/short grids; short-side research belongs in the isolated TFEX/generic profile"
                ],
            )

        if (
            config.market_profile == VideoEaMarketProfile.SET_EQUITY
            and bias == VideoEaBias.SHORT
            and config.grid_mode == VideoEaGridMode.PA_FILTERED
        ):
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
                research_only=True,
                executable=False,
                reasons=reasons
                + [
                    "SET-equity profile does not create a naked short ladder; bearish evidence is informational/exit-only"
                ],
            )

        if config.grid_mode == VideoEaGridMode.SYMMETRIC_RESEARCH and not request.research_only:
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
                research_only=True,
                executable=False,
                reasons=reasons
                + ["symmetric grid is restricted to research/paper planning and was not armed"],
            )

        if config.grid_mode == VideoEaGridMode.PA_FILTERED and bias == VideoEaBias.NEUTRAL:
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
                research_only=True,
                executable=False,
                reasons=reasons + ["PA-filtered mode does not seed a ladder without directional evidence"],
            )

        sides: list[Side]
        if config.grid_mode == VideoEaGridMode.SYMMETRIC_RESEARCH:
            sides = [Side.BUY, Side.SELL]
            reasons.append("symmetric stop-ladder reproduced in research-only mode")
        else:
            sides = [Side.BUY] if bias == VideoEaBias.LONG else [Side.SELL]
            reasons.append("ladder restricted to the PA-confirmed direction")

        max_by_quantity = config.max_total_quantity // config.quantity_per_level
        allowed_levels = min(
            config.levels_per_side,
            max_by_quantity // len(sides),
            config.max_pending_triggers // len(sides),
        )
        triggers: list[VideoEaTrigger] = []
        for side in sides:
            for level in range(1, allowed_levels + 1):
                raw_price = anchor + (step * level) if side == Side.BUY else anchor - (step * level)
                trigger_price = self._round_to_tick(raw_price, config.tick_size)
                triggers.append(
                    VideoEaTrigger(
                        side=side,
                        level=level,
                        trigger_price=trigger_price,
                        quantity=config.quantity_per_level,
                        dedupe_key=f"video-ea:{symbol}:{side.value}:{level}:{trigger_price:.10f}",
                    )
                )

        if allowed_levels < config.levels_per_side:
            reasons.append("ladder truncated by hard quantity/pending-trigger caps")
        reasons.append("fixed-size ladder only; martingale and duplicate stacking are intentionally absent")

        invalidation: float | None = None
        if zone is not None:
            risk_distance = max(atr_value * config.cycle_stop_r, step)
            if bias == VideoEaBias.LONG:
                invalidation = self._round_to_tick(
                    min(zone.low - risk_distance, anchor - risk_distance),
                    config.tick_size,
                )
            elif bias == VideoEaBias.SHORT:
                invalidation = self._round_to_tick(
                    max(zone.high + risk_distance, anchor + risk_distance),
                    config.tick_size,
                )

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
        triggered: list[VideoEaTrigger] = []
        for trigger in request.plan.triggers:
            if (
                trigger.side == Side.BUY
                and request.previous_price < trigger.trigger_price <= request.current_price
            ):
                triggered.append(trigger)
            elif (
                trigger.side == Side.SELL
                and request.previous_price > trigger.trigger_price >= request.current_price
            ):
                triggered.append(trigger)
        return VideoEaActivationResult(
            symbol=request.plan.symbol,
            triggered=triggered,
            executable=False,
            reason=(
                "virtual trigger crossings detected; any order must be rebuilt server-side and pass TradingService/RiskEngine"
                if triggered
                else "no virtual trigger crossed"
            ),
        )

    def _detect_pa_structure(
        self,
        candles: list[Candle],
        atr_value: float,
        config: VideoEaConfig,
    ) -> tuple[VideoEaBias, VideoEaZone | None, list[str]]:
        pivots_high = self._pivot_highs(candles, config.pivot_window)
        pivots_low = self._pivot_lows(candles, config.pivot_window)
        breakout_buffer = atr_value * config.breakout_buffer_atr
        retest_tolerance = atr_value * config.retest_tolerance_atr
        zone_half = atr_value * config.zone_half_width_atr

        candidates: list[tuple[int, VideoEaBias, VideoEaZone, str]] = []
        for pivot_index, level in pivots_high:
            for breakout_index in range(pivot_index + 1, len(candles) - 1):
                if candles[breakout_index].close <= level + breakout_buffer:
                    continue
                for retest_index in range(breakout_index + 1, len(candles)):
                    candle = candles[retest_index]
                    touched = candle.low <= level + retest_tolerance
                    held = candle.close >= level - retest_tolerance
                    confirmed = (not config.require_pa_confirmation) or self._bullish_pa(
                        candles,
                        retest_index,
                        config.rejection_wick_ratio,
                    )
                    if touched and held and confirmed:
                        candidates.append(
                            (
                                retest_index,
                                VideoEaBias.LONG,
                                VideoEaZone(
                                    kind="support",
                                    level=level,
                                    low=max(config.tick_size, level - zone_half),
                                    high=level + zone_half,
                                    source_index=pivot_index,
                                    breakout_index=breakout_index,
                                    retest_index=retest_index,
                                ),
                                "bullish breakout-retest / resistance-to-support flip detected",
                            )
                        )
                        break
                break

        for pivot_index, level in pivots_low:
            for breakout_index in range(pivot_index + 1, len(candles) - 1):
                if candles[breakout_index].close >= level - breakout_buffer:
                    continue
                for retest_index in range(breakout_index + 1, len(candles)):
                    candle = candles[retest_index]
                    touched = candle.high >= level - retest_tolerance
                    held = candle.close <= level + retest_tolerance
                    confirmed = (not config.require_pa_confirmation) or self._bearish_pa(
                        candles,
                        retest_index,
                        config.rejection_wick_ratio,
                    )
                    if touched and held and confirmed:
                        candidates.append(
                            (
                                retest_index,
                                VideoEaBias.SHORT,
                                VideoEaZone(
                                    kind="resistance",
                                    level=level,
                                    low=max(config.tick_size, level - zone_half),
                                    high=level + zone_half,
                                    source_index=pivot_index,
                                    breakout_index=breakout_index,
                                    retest_index=retest_index,
                                ),
                                "bearish breakout-retest / support-to-resistance flip detected",
                            )
                        )
                        break
                break

        if candidates:
            latest = max(candidates, key=lambda item: item[0])
            return latest[1], latest[2], [latest[3]]

        # Fallback: direct rejection at a recent swing zone, matching the first PA
        # example in the supplied teaching clip before a full S/R flip is visible.
        last_index = len(candles) - 1
        last = candles[last_index]
        if pivots_low:
            pivot_index, level = pivots_low[-1]
            if (
                last.low <= level + retest_tolerance
                and last.close >= level
                and self._bullish_pa(candles, last_index, config.rejection_wick_ratio)
            ):
                return (
                    VideoEaBias.LONG,
                    VideoEaZone(
                        kind="support",
                        level=level,
                        low=max(config.tick_size, level - zone_half),
                        high=level + zone_half,
                        source_index=pivot_index,
                        retest_index=last_index,
                    ),
                    ["bullish PA rejection from a recent support/demand zone detected"],
                )
        if pivots_high:
            pivot_index, level = pivots_high[-1]
            if (
                last.high >= level - retest_tolerance
                and last.close <= level
                and self._bearish_pa(candles, last_index, config.rejection_wick_ratio)
            ):
                return (
                    VideoEaBias.SHORT,
                    VideoEaZone(
                        kind="resistance",
                        level=level,
                        low=max(config.tick_size, level - zone_half),
                        high=level + zone_half,
                        source_index=pivot_index,
                        retest_index=last_index,
                    ),
                    ["bearish PA rejection from a recent resistance/supply zone detected"],
                )

        return VideoEaBias.NEUTRAL, None, ["no confirmed PA rejection or breakout-retest structure"]

    @staticmethod
    def _pivot_highs(candles: list[Candle], window: int) -> list[tuple[int, float]]:
        rows: list[tuple[int, float]] = []
        for index in range(window, len(candles) - window):
            value = candles[index].high
            before = candles[index - window : index]
            after = candles[index + 1 : index + window + 1]
            if all(value >= item.high for item in before) and all(value > item.high for item in after):
                rows.append((index, value))
        return rows

    @staticmethod
    def _pivot_lows(candles: list[Candle], window: int) -> list[tuple[int, float]]:
        rows: list[tuple[int, float]] = []
        for index in range(window, len(candles) - window):
            value = candles[index].low
            before = candles[index - window : index]
            after = candles[index + 1 : index + window + 1]
            if all(value <= item.low for item in before) and all(value < item.low for item in after):
                rows.append((index, value))
        return rows

    @staticmethod
    def _bullish_pa(candles: list[Candle], index: int, wick_ratio: float) -> bool:
        candle = candles[index]
        body = max(abs(candle.close - candle.open), 1e-12)
        lower_wick = min(candle.open, candle.close) - candle.low
        bullish_rejection = candle.close >= candle.open and lower_wick >= body * wick_ratio
        bullish_engulfing = False
        if index > 0:
            previous = candles[index - 1]
            bullish_engulfing = (
                previous.close < previous.open
                and candle.close > candle.open
                and candle.close >= previous.open
                and candle.open <= previous.close
            )
        return bullish_rejection or bullish_engulfing

    @staticmethod
    def _bearish_pa(candles: list[Candle], index: int, wick_ratio: float) -> bool:
        candle = candles[index]
        body = max(abs(candle.close - candle.open), 1e-12)
        upper_wick = candle.high - max(candle.open, candle.close)
        bearish_rejection = candle.close <= candle.open and upper_wick >= body * wick_ratio
        bearish_engulfing = False
        if index > 0:
            previous = candles[index - 1]
            bearish_engulfing = (
                previous.close > previous.open
                and candle.close < candle.open
                and candle.open >= previous.close
                and candle.close <= previous.open
            )
        return bearish_rejection or bearish_engulfing

    @staticmethod
    def _round_to_tick(value: float, tick_size: float) -> float:
        ticks = floor((value / tick_size) + 0.5)
        return max(tick_size, ticks * tick_size)
