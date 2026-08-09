from datetime import UTC, datetime, timedelta

from zksato.domain import Candle, Side
from zksato.market_rules import InstrumentMetadata
from zksato.video_ea import (
    VideoDerivedEaPlanner,
    VideoEaActivationRequest,
    VideoEaBias,
    VideoEaConfig,
    VideoEaGridMode,
    VideoEaMarketProfile,
    VideoEaPlanRequest,
)


def _candle(index: int, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(
        timestamp=datetime(2026, 8, 9, tzinfo=UTC) + timedelta(minutes=index),
        open=open_,
        high=high,
        low=low,
        close=close,
    )


def _bullish_breakout_retest() -> list[Candle]:
    closes = [
        100.0,
        100.2,
        100.4,
        100.1,
        100.5,
        100.8,
        101.0,
        101.5,
        102.0,
        101.4,
        101.2,
        101.4,
        101.6,
        102.6,
        103.0,
        103.2,
        102.7,
        102.5,
        102.3,
        102.45,
    ]
    candles: list[Candle] = []
    for index, close in enumerate(closes):
        open_ = close - 0.1
        high = close + 0.2
        low = close - 0.2
        if index == 8:
            high = 102.2
        if index == 18:
            open_ = 102.5
            close = 102.3
            low = 101.95
            high = 102.55
        if index == 19:
            open_ = 102.15
            close = 102.45
            low = 101.95
            high = 102.55
        candles.append(_candle(index, open_, high, low, close))
    return candles


def _config(**updates: object) -> VideoEaConfig:
    base = VideoEaConfig(
        atr_period=5,
        lookback_bars=20,
        pivot_window=2,
        grid_step_abs=0.30,
        tick_size=0.01,
        levels_per_side=7,
        max_total_quantity=5,
        max_pending_triggers=10,
    )
    return base.model_copy(update=updates)


def test_pa_filtered_set_plan_is_long_only_and_bounded() -> None:
    plan = VideoDerivedEaPlanner().plan(
        VideoEaPlanRequest(
            symbol="aot",
            candles=_bullish_breakout_retest(),
            config=_config(),
        )
    )

    assert plan.symbol == "AOT"
    assert plan.bias == VideoEaBias.LONG
    assert plan.zone is not None
    assert plan.zone.kind == "support"
    assert plan.grid_step == 0.30
    assert len(plan.triggers) == 5
    assert all(trigger.side == Side.BUY for trigger in plan.triggers)
    assert all(trigger.quantity == 1 for trigger in plan.triggers)
    assert sum(trigger.quantity for trigger in plan.triggers) <= plan.max_total_quantity
    assert plan.invalidation_price is not None
    assert plan.invalidation_price < plan.zone.low
    assert plan.research_only is True
    assert plan.executable is False
    assert any("martingale" in reason for reason in plan.reasons)


def test_virtual_trigger_activation_detects_crossings_only() -> None:
    planner = VideoDerivedEaPlanner()
    plan = planner.plan(
        VideoEaPlanRequest(
            symbol="AOT",
            candles=_bullish_breakout_retest(),
            config=_config(),
        )
    )

    result = planner.activate(
        VideoEaActivationRequest(
            plan=plan,
            previous_price=102.70,
            current_price=103.10,
        )
    )

    assert [trigger.level for trigger in result.triggered] == [1, 2]
    assert result.executable is False
    assert "RiskEngine" in result.reason


def test_set_equity_rejects_symmetric_grid() -> None:
    plan = VideoDerivedEaPlanner().plan(
        VideoEaPlanRequest(
            symbol="AOT",
            candles=_bullish_breakout_retest(),
            config=_config(grid_mode=VideoEaGridMode.SYMMETRIC_RESEARCH),
        )
    )

    assert plan.triggers == []
    assert plan.executable is False
    assert any("SET-equity" in reason for reason in plan.reasons)


def test_generic_symmetric_research_reproduces_two_sided_ladder_with_caps() -> None:
    plan = VideoDerivedEaPlanner().plan(
        VideoEaPlanRequest(
            symbol="XAUUSD",
            candles=_bullish_breakout_retest(),
            config=_config(
                grid_mode=VideoEaGridMode.SYMMETRIC_RESEARCH,
                market_profile=VideoEaMarketProfile.GENERIC_RESEARCH,
                max_total_quantity=8,
                max_pending_triggers=8,
                levels_per_side=10,
            ),
        )
    )

    assert len(plan.triggers) == 8
    assert sum(trigger.side == Side.BUY for trigger in plan.triggers) == 4
    assert sum(trigger.side == Side.SELL for trigger in plan.triggers) == 4
    assert sum(trigger.quantity for trigger in plan.triggers) == 8
    assert plan.executable is False


def test_insufficient_history_fails_closed_without_triggers() -> None:
    candles = _bullish_breakout_retest()[:8]
    plan = VideoDerivedEaPlanner().plan(
        VideoEaPlanRequest(
            symbol="AOT",
            candles=candles,
            config=_config(atr_period=14),
        )
    )

    assert plan.bias == VideoEaBias.NEUTRAL
    assert plan.triggers == []
    assert plan.executable is False


def test_set_instrument_rules_adapt_tick_and_price_band_without_crossing_limits() -> None:
    metadata = InstrumentMetadata(
        symbol="AOT",
        tick_size=0.25,
        lower_price_band=102.0,
        upper_price_band=103.0,
    )
    config = VideoEaConfig.for_instrument(
        metadata,
        atr_period=5,
        lookback_bars=20,
        pivot_window=2,
        grid_step_abs=0.30,
        levels_per_side=7,
        max_total_quantity=5,
        max_pending_triggers=10,
    )
    plan = VideoDerivedEaPlanner().plan(
        VideoEaPlanRequest(symbol="AOT", candles=_bullish_breakout_retest(), config=config)
    )

    assert config.tick_size == 0.25
    assert config.lower_price_band == 102.0
    assert config.upper_price_band == 103.0
    assert all(102.0 <= trigger.trigger_price <= 103.0 for trigger in plan.triggers)
    assert all(
        abs((trigger.trigger_price / 0.25) - round(trigger.trigger_price / 0.25)) < 1e-7
        for trigger in plan.triggers
    )


def test_video_ea_fails_closed_when_anchor_is_outside_price_band() -> None:
    plan = VideoDerivedEaPlanner().plan(
        VideoEaPlanRequest(
            symbol="AOT",
            candles=_bullish_breakout_retest(),
            config=_config(upper_price_band=102.0),
        )
    )

    assert plan.triggers == []
    assert any("price band" in reason for reason in plan.reasons)
