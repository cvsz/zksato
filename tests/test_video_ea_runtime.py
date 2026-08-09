import pytest

from zksato.domain import Side
from zksato.video_ea import VideoEaBias, VideoEaPlan, VideoEaTrigger
from zksato.video_ea_runtime import VideoEaCycleRuntime, VideoEaCycleState


def _plan() -> VideoEaPlan:
    return VideoEaPlan(
        symbol="AOT",
        bias=VideoEaBias.LONG,
        anchor_price=100.0,
        atr=1.0,
        grid_step=1.0,
        triggers=[
            VideoEaTrigger(
                side=Side.BUY,
                level=1,
                trigger_price=101.0,
                quantity=100,
                dedupe_key="aot-buy-1",
            ),
            VideoEaTrigger(
                side=Side.BUY,
                level=2,
                trigger_price=102.0,
                quantity=100,
                dedupe_key="aot-buy-2",
            ),
        ],
        invalidation_price=98.0,
        basket_take_profit_r=1.5,
        cycle_stop_r=1.0,
        max_total_quantity=200,
    )


def test_runtime_deduplicates_trigger_crossings() -> None:
    runtime = VideoEaCycleRuntime()
    runtime.arm(_plan(), current_price=100.0)

    first = runtime.on_price(101.5)
    assert [item.level for item in first.triggers] == [1]
    assert first.executable is False

    runtime.on_price(100.5)
    repeated = runtime.on_price(101.5)
    assert repeated.triggers == []

    second = runtime.on_price(102.5)
    assert [item.level for item in second.triggers] == [2]
    assert runtime.snapshot().fired_quantity == 200


def test_runtime_rejects_rearm_while_cycle_is_active() -> None:
    runtime = VideoEaCycleRuntime()
    runtime.arm(_plan(), current_price=100.0)

    with pytest.raises(ValueError, match="reset"):
        runtime.arm(_plan(), current_price=100.5)

    runtime.on_price(101.5)
    with pytest.raises(ValueError, match="reset"):
        runtime.arm(_plan(), current_price=101.5)


def test_runtime_basket_boundaries_are_terminal_until_reset() -> None:
    runtime = VideoEaCycleRuntime()
    runtime.arm(_plan(), current_price=100.0)
    runtime.on_price(101.5)

    event = runtime.on_basket_pnl_r(1.5)
    assert event.state == VideoEaCycleState.TAKE_PROFIT
    assert runtime.on_price(102.5).event_type == "cycle.closed"

    repeated = runtime.on_basket_pnl_r(-10.0)
    assert repeated.event_type == "cycle.closed"
    assert repeated.state == VideoEaCycleState.TAKE_PROFIT

    runtime.reset()
    assert runtime.snapshot().state == VideoEaCycleState.IDLE


def test_runtime_stop_state_cannot_be_overwritten_by_later_profit() -> None:
    runtime = VideoEaCycleRuntime()
    runtime.arm(_plan(), current_price=100.0)

    stopped = runtime.on_basket_pnl_r(-1.0)
    assert stopped.state == VideoEaCycleState.STOPPED

    later = runtime.on_basket_pnl_r(5.0)
    assert later.event_type == "cycle.closed"
    assert later.state == VideoEaCycleState.STOPPED


def test_runtime_fails_closed_on_invalidation() -> None:
    runtime = VideoEaCycleRuntime()
    runtime.arm(_plan(), current_price=100.0)

    event = runtime.on_price(97.9)
    assert event.state == VideoEaCycleState.INVALIDATED
    assert event.triggers == []
    assert runtime.snapshot().executable is False

    later = runtime.on_basket_pnl_r(5.0)
    assert later.event_type == "cycle.closed"
    assert later.state == VideoEaCycleState.INVALIDATED


def test_runtime_snapshot_recovers_plan_and_trigger_dedupe_after_restart() -> None:
    runtime = VideoEaCycleRuntime()
    runtime.arm(_plan(), current_price=100.0)
    runtime.on_price(101.5)

    snapshot = runtime.snapshot()
    assert snapshot.plan == _plan()

    recovered = VideoEaCycleRuntime.from_snapshot(snapshot.model_dump(mode="json"))
    assert recovered.snapshot() == snapshot

    recovered.on_price(100.5)
    repeated = recovered.on_price(101.5)
    assert repeated.triggers == []


def test_runtime_snapshot_rejects_execution_authority() -> None:
    runtime = VideoEaCycleRuntime()
    runtime.arm(_plan(), current_price=100.0)
    snapshot = runtime.snapshot().model_copy(update={"executable": True})

    with pytest.raises(ValueError, match="non-executable"):
        VideoEaCycleRuntime.from_snapshot(snapshot)


def test_runtime_pause_blocks_price_until_explicit_resume() -> None:
    runtime = VideoEaCycleRuntime()
    runtime.arm(_plan(), current_price=100.0)

    paused = runtime.pause()
    assert paused.state == VideoEaCycleState.PAUSED
    assert runtime.on_price(103.0).event_type == "cycle.paused"

    resumed = runtime.resume()
    assert resumed.state == VideoEaCycleState.ARMED
    assert [item.level for item in runtime.on_price(103.0).triggers] == [1, 2]
