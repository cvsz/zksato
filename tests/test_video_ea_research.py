from datetime import UTC, datetime, timedelta

from zksato.domain import Candle, Side, StrategyConfig, StrategyRun, StrategyVersion
from zksato.video_ea import VideoEaBias, VideoEaConfig, VideoEaPlan, VideoEaTrigger
from zksato.video_ea_research import (
    BasketLifecycleRequest,
    MonteCarloTradeStressRequest,
    ParameterSweepRequest,
    RollingWalkForwardRequest,
    SensitivityRequest,
    StrategyRunEvidenceRequest,
    VideoEaReplayRequest,
    basket_lifecycle_metrics,
    build_strategy_run_evidence,
    max_exposure_heatmap,
    monte_carlo_trade_stress,
    parameter_sweep,
    replay_video_ea,
    rolling_walk_forward,
    sensitivity_analysis,
    simulate_grid_whipsaw,
)
from zksato.video_ea_runtime import VideoEaCycleRuntime


def _candles(count: int = 48) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    prices = [100, 101, 99, 102, 98, 103, 100, 104, 101, 105]
    return [
        Candle(
            timestamp=start + timedelta(minutes=index),
            open=prices[index % len(prices)],
            high=prices[index % len(prices)] + 1,
            low=prices[index % len(prices)] - 1,
            close=prices[index % len(prices)] + (index * 0.05),
            volume=1000 + index,
        )
        for index in range(count)
    ]


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


def test_historical_replay_and_whipsaw_keep_gap_crossings_deterministic() -> None:
    request = VideoEaReplayRequest(
        symbol="AOT",
        candles=_candles(),
        config=VideoEaConfig(
            market_profile="generic_research",  # type: ignore[arg-type]
            grid_mode="symmetric_research",  # type: ignore[arg-type]
            lookback_bars=30,
            levels_per_side=2,
            max_total_quantity=4,
            max_pending_triggers=4,
        ),
    )
    first = replay_video_ea(request)
    second = replay_video_ea(request)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.bars_replayed == len(request.candles)

    stress = simulate_grid_whipsaw(_plan(), [100.0, 103.0, 100.0, 103.0])
    assert stress.unique_trigger_count == 2
    assert stress.duplicate_crossings == 2
    assert stress.max_fired_quantity == 200


def test_exposure_heatmap_and_basket_lifecycle_metrics_are_bounded() -> None:
    plan = _plan()
    heatmap = max_exposure_heatmap(plan, [101.0, 102.0], portfolio_value=100_000)
    assert heatmap.cells[-1].quantity == 200
    assert heatmap.cells[-1].exposure_pct == 20.4

    runtime = VideoEaCycleRuntime()
    runtime.arm(plan, current_price=100.0)
    events = [runtime.on_price(101.5), runtime.on_basket_pnl_r(1.5)]
    metrics = basket_lifecycle_metrics(
        BasketLifecycleRequest(events=events, snapshots=[runtime.snapshot()])
    )
    assert metrics.trigger_events == 1
    assert metrics.take_profit_events == 1
    assert metrics.total_trigger_quantity == 100
    assert metrics.final_state == "take_profit"


def test_parameter_sweep_and_rolling_walk_forward_are_repeatable() -> None:
    base = dict(
        symbol="AOT",
        candles=_candles(),
        base_strategy=StrategyConfig(min_history=5, fast_period=2, slow_period=4),
        initial_cash=100_000,
        order_size=10,
    )
    sweep = parameter_sweep(
        ParameterSweepRequest(
            **base,  # type: ignore[arg-type]
            parameter_grid={"fast_period": [2, 3], "slow_period": [4]},
        )
    )
    assert sweep.combinations == 2
    assert len(sweep.rows) == 2
    assert sweep.best_parameters in [
        {"fast_period": 2, "slow_period": 4},
        {"fast_period": 3, "slow_period": 4},
    ]

    rolling_request = RollingWalkForwardRequest(
        **base,  # type: ignore[arg-type]
        train_size=20,
        test_size=10,
        step_size=10,
    )
    first = rolling_walk_forward(rolling_request)
    second = rolling_walk_forward(rolling_request)
    assert len(first.windows) == 2
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_monte_carlo_and_execution_cost_sensitivity_are_seeded_and_bounded() -> None:
    monte = monte_carlo_trade_stress(
        MonteCarloTradeStressRequest(
            trade_pnls=[10.0, -5.0, 2.0, -1.0],
            simulations=100,
            seed=42,
        )
    )
    assert monte == monte_carlo_trade_stress(
        MonteCarloTradeStressRequest(
            trade_pnls=[10.0, -5.0, 2.0, -1.0],
            simulations=100,
            seed=42,
        )
    )
    assert monte.worst_drawdown_pct >= 0
    assert monte.minimum_final_equity <= monte.median_final_equity

    sensitivity = sensitivity_analysis(
        SensitivityRequest(
            symbol="AOT",
            candles=_candles(),
            strategy=StrategyConfig(min_history=5, fast_period=2, slow_period=4),
            commission_pcts=[0.1, 0.2],
            slippage_pcts=[0.0, 0.1],
            spread_pcts=[0.0, 0.2],
            order_size=10,
        )
    )
    assert len(sensitivity.cells) == 8
    assert sensitivity.cells[0].effective_slippage_pct == 0.0


def test_strategy_run_evidence_hashes_version_and_run_content() -> None:
    version = StrategyVersion(
        name="ema_cross",
        version="2026.08.09",
        config={"fast_period": 2},
        code_hash="a" * 64,
    )
    run = StrategyRun(
        strategy="ema_cross",
        symbol="AOT",
        inputs={"bars": 48},
        output={"return_pct": 2.5},
    )
    evidence = build_strategy_run_evidence(StrategyRunEvidenceRequest(run=run, version=version))
    assert evidence.strategy_version_id == version.id
    assert evidence.strategy_run_id == run.id
    assert len(evidence.evidence_hash) == 64
    assert (
        evidence.evidence_hash
        == build_strategy_run_evidence(
            StrategyRunEvidenceRequest(run=run, version=version)
        ).evidence_hash
    )
