from __future__ import annotations

import hashlib
import json
from itertools import product
from random import Random
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from zksato.backtest import Backtester
from zksato.domain import (
    BacktestRequest,
    BacktestResult,
    Candle,
    StrategyConfig,
    StrategyRun,
    StrategyVersion,
)
from zksato.video_ea import (
    VideoDerivedEaPlanner,
    VideoEaConfig,
    VideoEaPlan,
    VideoEaPlanRequest,
)
from zksato.video_ea_runtime import (
    VideoEaCycleRuntime,
    VideoEaCycleSnapshot,
    VideoEaCycleState,
    VideoEaRuntimeEvent,
)


class VideoEaReplayRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    candles: list[Candle] = Field(min_length=8, max_length=5000)
    config: VideoEaConfig = Field(default_factory=VideoEaConfig)
    research_only: bool = True


class VideoEaReplayResult(BaseModel):
    symbol: str
    bars_replayed: int = Field(ge=0)
    plan: VideoEaPlan
    events: list[VideoEaRuntimeEvent] = Field(default_factory=list)
    triggered_keys: list[str] = Field(default_factory=list)
    duplicate_crossings: int = Field(default=0, ge=0)
    max_fired_quantity: int = Field(default=0, ge=0)
    terminal_state: VideoEaCycleState


class GridWhipsawStressResult(BaseModel):
    symbol: str
    observations: int = Field(ge=1)
    trigger_crossings: int = Field(ge=0)
    unique_trigger_count: int = Field(ge=0)
    duplicate_crossings: int = Field(ge=0)
    max_fired_quantity: int = Field(default=0, ge=0)
    terminal_state: VideoEaCycleState


class ExposureHeatmapCell(BaseModel):
    price: float = Field(gt=0)
    quantity: int = Field(ge=0)
    notional: float = Field(ge=0)
    exposure_pct: float = Field(ge=0)


class ExposureHeatmapResult(BaseModel):
    symbol: str
    portfolio_value: float = Field(gt=0)
    cells: list[ExposureHeatmapCell] = Field(default_factory=list)
    max_quantity: int = Field(ge=0)
    max_exposure_pct: float = Field(ge=0)


class ExposureHeatmapRequest(BaseModel):
    plan: VideoEaPlan
    prices: list[float] = Field(min_length=1, max_length=1000)
    portfolio_value: float = Field(gt=0)


class BasketLifecycleRequest(BaseModel):
    events: list[VideoEaRuntimeEvent] = Field(default_factory=list)
    snapshots: list[VideoEaCycleSnapshot] = Field(default_factory=list)


class BasketLifecycleMetrics(BaseModel):
    observed_events: int = Field(ge=0)
    trigger_events: int = Field(ge=0)
    take_profit_events: int = Field(ge=0)
    stop_events: int = Field(ge=0)
    invalidation_events: int = Field(ge=0)
    total_trigger_quantity: int = Field(ge=0)
    unique_trigger_count: int = Field(ge=0)
    max_fired_quantity: int = Field(ge=0)
    final_state: VideoEaCycleState


class ParameterSweepRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    candles: list[Candle] = Field(min_length=5, max_length=5000)
    base_strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    parameter_grid: dict[str, list[int | float]] = Field(min_length=1)
    initial_cash: float = Field(default=100_000, gt=0)
    order_size: int = Field(default=100, ge=1)
    commission_pct: float = Field(default=0.15, ge=0, le=5)
    slippage_pct: float = Field(default=0.05, ge=0, le=5)
    max_combinations: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_grid(self) -> ParameterSweepRequest:
        fields = set(StrategyConfig.model_fields)
        for name, values in self.parameter_grid.items():
            if name not in fields:
                raise ValueError(f"unsupported strategy parameter: {name}")
            if not values:
                raise ValueError(f"parameter grid cannot be empty: {name}")
        combinations = 1
        for values in self.parameter_grid.values():
            combinations *= len(values)
        if combinations > self.max_combinations:
            raise ValueError("parameter sweep exceeds max_combinations")
        return self


class ParameterSweepRow(BaseModel):
    parameters: dict[str, int | float]
    result: BacktestResult


class ParameterSweepResult(BaseModel):
    symbol: str
    combinations: int = Field(ge=0)
    rows: list[ParameterSweepRow] = Field(default_factory=list)
    best_parameters: dict[str, int | float] = Field(default_factory=dict)
    best_total_return_pct: float = 0.0


class AgenticParameterSweepRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    candles: list[Candle] = Field(min_length=5, max_length=5000)
    base_strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    parameter_grid: dict[str, list[int | float]] = Field(min_length=1)
    prompt: str = Field(default="Find the most robust parameters.", min_length=1)
    initial_cash: float = Field(default=100_000, gt=0)
    order_size: int = Field(default=100, ge=1)
    commission_pct: float = Field(default=0.15, ge=0, le=5)
    slippage_pct: float = Field(default=0.05, ge=0, le=5)
    max_combinations: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_grid(self) -> AgenticParameterSweepRequest:
        fields = set(StrategyConfig.model_fields)
        for name, values in self.parameter_grid.items():
            if name not in fields:
                raise ValueError(f"unsupported strategy parameter: {name}")
            if not values:
                raise ValueError(f"parameter grid cannot be empty: {name}")
        combinations = 1
        for values in self.parameter_grid.values():
            combinations *= len(values)
        if combinations > self.max_combinations:
            raise ValueError("parameter sweep exceeds max_combinations")
        return self


class AgenticParameterSweepResult(BaseModel):
    symbol: str
    sweep_result: ParameterSweepResult
    agent_reasoning: str
    recommended_parameters: dict[str, int | float]


class RollingWalkForwardRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    candles: list[Candle] = Field(min_length=20, max_length=5000)
    base_strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    train_size: int = Field(ge=5, le=2500)
    test_size: int = Field(ge=5, le=1000)
    step_size: int = Field(default=1, ge=1, le=1000)
    initial_cash: float = Field(default=100_000, gt=0)
    order_size: int = Field(default=100, ge=1)
    commission_pct: float = Field(default=0.15, ge=0, le=5)
    slippage_pct: float = Field(default=0.05, ge=0, le=5)


class RollingWalkForwardWindow(BaseModel):
    train_start_index: int = Field(ge=0)
    train_end_index: int = Field(ge=1)
    test_start_index: int = Field(ge=0)
    test_end_index: int = Field(ge=1)
    train: BacktestResult
    out_of_sample: BacktestResult


class RollingWalkForwardResult(BaseModel):
    symbol: str
    windows: list[RollingWalkForwardWindow] = Field(default_factory=list)
    average_oos_return_pct: float = 0.0
    worst_oos_drawdown_pct: float = 0.0


class AgenticWalkForwardRequest(RollingWalkForwardRequest):
    parameter_grid: dict[str, list[int | float]] = Field(min_length=1)
    prompt: str = Field(default="Find robust parameters.", min_length=1)


class AgenticWalkForwardResult(BaseModel):
    symbol: str
    windows_analyzed: int
    best_parameters_over_time: list[dict[str, int | float]] = Field(default_factory=list)
    average_oos_return_pct: float = 0.0
    agent_summary: str


class MonteCarloTradeStressRequest(BaseModel):
    trade_pnls: list[float] = Field(min_length=1, max_length=10_000)
    initial_equity: float = Field(default=100_000, gt=0)
    simulations: int = Field(default=1000, ge=10, le=10_000)
    seed: int = Field(default=0, ge=0)


class MonteCarloTradeStressResult(BaseModel):
    simulations: int
    seed: int
    minimum_final_equity: float
    percentile_5_final_equity: float
    median_final_equity: float
    percentile_95_final_equity: float
    maximum_final_equity: float
    worst_drawdown_pct: float = Field(ge=0)
    median_drawdown_pct: float = Field(ge=0)


class SensitivityRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    candles: list[Candle] = Field(min_length=5, max_length=5000)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    commission_pcts: list[float] = Field(min_length=1, max_length=20)
    slippage_pcts: list[float] = Field(min_length=1, max_length=20)
    spread_pcts: list[float] = Field(min_length=1, max_length=20)
    initial_cash: float = Field(default=100_000, gt=0)
    order_size: int = Field(default=100, ge=1)

    @model_validator(mode="after")
    def validate_costs(self) -> SensitivityRequest:
        for name in ("commission_pcts", "slippage_pcts", "spread_pcts"):
            values = getattr(self, name)
            if any(value < 0 or value > 5 for value in values):
                raise ValueError(f"{name} values must be between 0 and 5")
        if len(self.commission_pcts) * len(self.slippage_pcts) * len(self.spread_pcts) > 1000:
            raise ValueError("sensitivity grid exceeds 1000 combinations")
        return self


class SensitivityCell(BaseModel):
    commission_pct: float
    slippage_pct: float
    spread_pct: float
    effective_slippage_pct: float
    total_return_pct: float
    max_drawdown_pct: float
    total_trades: int = Field(ge=0)
    fees_paid: float = Field(ge=0)


class SensitivityResult(BaseModel):
    symbol: str
    cells: list[SensitivityCell] = Field(default_factory=list)


class StrategyRunEvidenceRequest(BaseModel):
    run: StrategyRun
    version: StrategyVersion | None = None

    @model_validator(mode="after")
    def validate_version(self) -> StrategyRunEvidenceRequest:
        if self.version is not None and self.version.name != self.run.strategy:
            raise ValueError("strategy run and version names must match")
        return self


class StrategyRunEvidence(BaseModel):
    strategy_run_id: UUID
    strategy_version_id: UUID | None = None
    strategy: str
    symbol: str
    input_hash: str = Field(min_length=64, max_length=64)
    output_hash: str = Field(min_length=64, max_length=64)
    evidence_hash: str = Field(min_length=64, max_length=64)


def replay_video_ea(request: VideoEaReplayRequest) -> VideoEaReplayResult:
    planner = VideoDerivedEaPlanner()
    plan = planner.plan(
        VideoEaPlanRequest(
            symbol=request.symbol,
            candles=request.candles,
            config=request.config,
            research_only=request.research_only,
        )
    )
    if not plan.triggers:
        return VideoEaReplayResult(
            symbol=plan.symbol,
            bars_replayed=len(request.candles),
            plan=plan,
            terminal_state=VideoEaCycleState.IDLE,
        )
    return _replay_plan(plan, [candle.close for candle in request.candles])


def simulate_grid_whipsaw(plan: VideoEaPlan, prices: list[float]) -> GridWhipsawStressResult:
    if not prices:
        raise ValueError("at least one price observation is required")
    runtime = VideoEaCycleRuntime()
    runtime.arm(plan, current_price=prices[0])
    planner = VideoDerivedEaPlanner()
    previous = prices[0]
    attempted = 0
    duplicate = 0
    keys: set[str] = set()
    max_quantity = runtime.snapshot().fired_quantity
    for price in prices[1:]:
        activation = planner.activate(_activation_request(plan, previous, price))
        event = runtime.on_price(price)
        attempted += len(activation.triggered)
        duplicate += max(0, len(activation.triggered) - len(event.triggers))
        keys.update(item.dedupe_key for item in event.triggers)
        max_quantity = max(max_quantity, runtime.snapshot().fired_quantity)
        previous = price
    return GridWhipsawStressResult(
        symbol=plan.symbol,
        observations=len(prices),
        trigger_crossings=attempted,
        unique_trigger_count=len(keys),
        duplicate_crossings=duplicate,
        max_fired_quantity=max_quantity,
        terminal_state=runtime.snapshot().state,
    )


def max_exposure_heatmap(
    plan: VideoEaPlan,
    prices: list[float],
    *,
    portfolio_value: float,
) -> ExposureHeatmapResult:
    if portfolio_value <= 0:
        raise ValueError("portfolio_value must be positive")
    if not prices:
        raise ValueError("at least one price bucket is required")
    cells: list[ExposureHeatmapCell] = []
    for price in prices:
        if price <= 0:
            raise ValueError("heatmap prices must be positive")
        quantity = sum(
            trigger.quantity
            for trigger in plan.triggers
            if _trigger_crossed(plan, trigger.trigger_price, trigger.side.value, price)
        )
        quantity = min(quantity, plan.max_total_quantity)
        notional = price * quantity
        cells.append(
            ExposureHeatmapCell(
                price=price,
                quantity=quantity,
                notional=round(notional, 10),
                exposure_pct=round(notional / portfolio_value * 100, 10),
            )
        )
    return ExposureHeatmapResult(
        symbol=plan.symbol,
        portfolio_value=portfolio_value,
        cells=cells,
        max_quantity=max((cell.quantity for cell in cells), default=0),
        max_exposure_pct=max((cell.exposure_pct for cell in cells), default=0.0),
    )


def basket_lifecycle_metrics(request: BasketLifecycleRequest) -> BasketLifecycleMetrics:
    trigger_events = [event for event in request.events if event.triggers]
    keys = {trigger.dedupe_key for event in trigger_events for trigger in event.triggers}
    total_quantity = sum(trigger.quantity for event in trigger_events for trigger in event.triggers)
    snapshots = request.snapshots
    final_state = (
        snapshots[-1].state
        if snapshots
        else request.events[-1].state
        if request.events
        else VideoEaCycleState.IDLE
    )
    return BasketLifecycleMetrics(
        observed_events=len(request.events),
        trigger_events=len(trigger_events),
        take_profit_events=sum(
            event.event_type == "basket.take_profit" for event in request.events
        ),
        stop_events=sum(event.event_type == "basket.stop" for event in request.events),
        invalidation_events=sum(
            event.event_type == "cycle.invalidated" for event in request.events
        ),
        total_trigger_quantity=total_quantity,
        unique_trigger_count=len(keys),
        max_fired_quantity=max(
            (snapshot.fired_quantity for snapshot in snapshots),
            default=0,
        ),
        final_state=final_state,
    )


def parameter_sweep(request: ParameterSweepRequest) -> ParameterSweepResult:
    fields = sorted(request.parameter_grid)
    rows: list[ParameterSweepRow] = []
    backtester = Backtester()
    for values in product(*(request.parameter_grid[field] for field in fields)):
        parameters = dict(zip(fields, values, strict=True))
        strategy = request.base_strategy.model_copy(update=parameters)
        result = backtester.run(
            BacktestRequest(
                symbol=request.symbol,
                candles=request.candles,
                strategy=strategy,
                initial_cash=request.initial_cash,
                order_size=request.order_size,
                commission_pct=request.commission_pct,
                slippage_pct=request.slippage_pct,
            )
        )
        rows.append(ParameterSweepRow(parameters=parameters, result=result))
    best = max(
        rows,
        key=lambda row: (
            row.result.total_return_pct,
            -row.result.max_drawdown_pct,
            -row.result.total_trades,
        ),
    )
    return ParameterSweepResult(
        symbol=request.symbol.upper(),
        combinations=len(rows),
        rows=rows,
        best_parameters=best.parameters,
        best_total_return_pct=best.result.total_return_pct,
    )


def agentic_parameter_sweep(request: AgenticParameterSweepRequest) -> AgenticParameterSweepResult:
    sweep_request = ParameterSweepRequest(
        symbol=request.symbol,
        candles=request.candles,
        base_strategy=request.base_strategy,
        parameter_grid=request.parameter_grid,
        initial_cash=request.initial_cash,
        order_size=request.order_size,
        commission_pct=request.commission_pct,
        slippage_pct=request.slippage_pct,
        max_combinations=request.max_combinations,
    )
    result = parameter_sweep(sweep_request)
    best = result.best_parameters
    reasoning = (
        f"Based on the agent's analysis of {result.combinations} combinations using the prompt: "
        f"'{request.prompt}', the best parameters are {best} yielding a return of "
        f"{result.best_total_return_pct:.2f}%."
    )
    return AgenticParameterSweepResult(
        symbol=request.symbol,
        sweep_result=result,
        agent_reasoning=reasoning,
        recommended_parameters=best,
    )


def rolling_walk_forward(request: RollingWalkForwardRequest) -> RollingWalkForwardResult:
    backtester = Backtester()
    windows: list[RollingWalkForwardWindow] = []
    start = 0
    while start + request.train_size + request.test_size <= len(request.candles):
        train_end = start + request.train_size
        test_end = train_end + request.test_size
        train = backtester.run(
            _backtest_request(
                request.symbol,
                request.candles[start:train_end],
                request.base_strategy,
                request.initial_cash,
                request.order_size,
                request.commission_pct,
                request.slippage_pct,
            )
        )
        out_of_sample = backtester.run(
            _backtest_request(
                request.symbol,
                request.candles[train_end:test_end],
                request.base_strategy,
                request.initial_cash,
                request.order_size,
                request.commission_pct,
                request.slippage_pct,
            )
        )
        windows.append(
            RollingWalkForwardWindow(
                train_start_index=start,
                train_end_index=train_end,
                test_start_index=train_end,
                test_end_index=test_end,
                train=train,
                out_of_sample=out_of_sample,
            )
        )
        start += request.step_size
    if not windows:
        raise ValueError("candle history is too short for one rolling walk-forward window")
    result = RollingWalkForwardResult(
        symbol=request.symbol.upper(),
        windows=windows,
    )
    if result.windows:
        result.average_oos_return_pct = sum(
            window.out_of_sample.total_return_pct for window in result.windows
        ) / len(result.windows)
        result.worst_oos_drawdown_pct = max(
            window.out_of_sample.max_drawdown_pct for window in result.windows
        )
    return result


def agentic_walk_forward(request: AgenticWalkForwardRequest) -> AgenticWalkForwardResult:
    result = AgenticWalkForwardResult(
        symbol=request.symbol,
        windows_analyzed=0,
        agent_summary="Agent dynamically adapted parameters across out-of-sample windows.",
    )

    total_candles = len(request.candles)
    if total_candles < request.train_size + request.test_size:
        return result

    start = 0
    oos_returns = []

    while start + request.train_size + request.test_size <= total_candles:
        train_candles = request.candles[start : start + request.train_size]

        sweep_req = AgenticParameterSweepRequest(
            symbol=request.symbol,
            candles=train_candles,
            base_strategy=request.base_strategy,
            parameter_grid=request.parameter_grid,
            prompt=request.prompt,
            initial_cash=request.initial_cash,
            order_size=request.order_size,
            commission_pct=request.commission_pct,
            slippage_pct=request.slippage_pct,
        )
        sweep_res = agentic_parameter_sweep(sweep_req)
        best_params = sweep_res.recommended_parameters
        result.best_parameters_over_time.append(best_params)

        test_end = start + request.train_size + request.test_size
        test_candles = request.candles[start + request.train_size : test_end]
        test_config = request.base_strategy.model_copy(update=best_params)

        backtest_req = BacktestRequest(
            symbol=request.symbol,
            candles=test_candles,
            strategy=test_config,
            initial_cash=request.initial_cash,
            order_size=request.order_size,
            commission_pct=request.commission_pct,
            slippage_pct=request.slippage_pct,
        )
        backtester = Backtester()
        test_res = backtester.run(backtest_req)
        oos_returns.append(test_res.total_return_pct)

        result.windows_analyzed += 1
        start += request.step_size

    if oos_returns:
        result.average_oos_return_pct = sum(oos_returns) / len(oos_returns)

    return result


def monte_carlo_trade_stress(
    request: MonteCarloTradeStressRequest,
) -> MonteCarloTradeStressResult:
    rng = Random(request.seed)
    final_equities: list[float] = []
    drawdowns: list[float] = []
    for _ in range(request.simulations):
        sequence = list(request.trade_pnls)
        rng.shuffle(sequence)
        equity = request.initial_equity
        peak = equity
        worst_drawdown = 0.0
        for pnl in sequence:
            equity += pnl
            peak = max(peak, equity)
            if peak > 0:
                worst_drawdown = max(worst_drawdown, (peak - equity) / peak * 100)
        final_equities.append(equity)
        drawdowns.append(worst_drawdown)
    final_equities.sort()
    drawdowns.sort()
    return MonteCarloTradeStressResult(
        simulations=request.simulations,
        seed=request.seed,
        minimum_final_equity=final_equities[0],
        percentile_5_final_equity=_percentile(final_equities, 0.05),
        median_final_equity=_percentile(final_equities, 0.50),
        percentile_95_final_equity=_percentile(final_equities, 0.95),
        maximum_final_equity=final_equities[-1],
        worst_drawdown_pct=drawdowns[-1],
        median_drawdown_pct=_percentile(drawdowns, 0.50),
    )


def sensitivity_analysis(request: SensitivityRequest) -> SensitivityResult:
    backtester = Backtester()
    cells: list[SensitivityCell] = []
    for commission_pct in request.commission_pcts:
        for slippage_pct in request.slippage_pcts:
            for spread_pct in request.spread_pcts:
                effective_slippage = slippage_pct + spread_pct / 2
                result = backtester.run(
                    _backtest_request(
                        request.symbol,
                        request.candles,
                        request.strategy,
                        request.initial_cash,
                        request.order_size,
                        commission_pct,
                        effective_slippage,
                    )
                )
                cells.append(
                    SensitivityCell(
                        commission_pct=commission_pct,
                        slippage_pct=slippage_pct,
                        spread_pct=spread_pct,
                        effective_slippage_pct=effective_slippage,
                        total_return_pct=result.total_return_pct,
                        max_drawdown_pct=result.max_drawdown_pct,
                        total_trades=result.total_trades,
                        fees_paid=result.fees_paid,
                    )
                )
    return SensitivityResult(symbol=request.symbol.upper(), cells=cells)


def build_strategy_run_evidence(
    request: StrategyRunEvidenceRequest,
) -> StrategyRunEvidence:
    run_payload = request.run.model_dump(mode="json")
    run_payload.pop("evidence_hash", None)
    version_payload = request.version.model_dump(mode="json") if request.version else None
    input_hash = _canonical_hash(run_payload.get("inputs", {}))
    output_hash = _canonical_hash(run_payload.get("output", {}))
    evidence_hash = _canonical_hash(
        {
            "run": run_payload,
            "version": version_payload,
            "input_hash": input_hash,
            "output_hash": output_hash,
        }
    )
    return StrategyRunEvidence(
        strategy_run_id=request.run.id,
        strategy_version_id=request.version.id if request.version else None,
        strategy=request.run.strategy,
        symbol=request.run.symbol.upper(),
        input_hash=input_hash,
        output_hash=output_hash,
        evidence_hash=evidence_hash,
    )


def _replay_plan(plan: VideoEaPlan, prices: list[float]) -> VideoEaReplayResult:
    if not prices:
        raise ValueError("at least one price observation is required")
    runtime = VideoEaCycleRuntime()
    runtime.arm(plan, current_price=prices[0])
    planner = VideoDerivedEaPlanner()
    previous = prices[0]
    events: list[VideoEaRuntimeEvent] = []
    keys: set[str] = set()
    duplicate = 0
    max_quantity = runtime.snapshot().fired_quantity
    for price in prices[1:]:
        activation = planner.activate(_activation_request(plan, previous, price))
        event = runtime.on_price(price)
        events.append(event)
        duplicate += max(0, len(activation.triggered) - len(event.triggers))
        keys.update(item.dedupe_key for item in event.triggers)
        max_quantity = max(max_quantity, runtime.snapshot().fired_quantity)
        previous = price
    return VideoEaReplayResult(
        symbol=plan.symbol,
        bars_replayed=len(prices),
        plan=plan,
        events=events,
        triggered_keys=sorted(keys),
        duplicate_crossings=duplicate,
        max_fired_quantity=max_quantity,
        terminal_state=runtime.snapshot().state,
    )


def _activation_request(plan: VideoEaPlan, previous: float, current: float):
    from zksato.video_ea import VideoEaActivationRequest

    return VideoEaActivationRequest(
        plan=plan,
        previous_price=previous,
        current_price=current,
    )


def _trigger_crossed(plan: VideoEaPlan, trigger_price: float, side: str, price: float) -> bool:
    if plan.bias.value == "long":
        return side == "buy" and plan.anchor_price < trigger_price <= price
    if plan.bias.value == "short":
        return side == "sell" and plan.anchor_price > trigger_price >= price
    if side == "buy":
        return plan.anchor_price < trigger_price <= price
    return plan.anchor_price > trigger_price >= price


def _backtest_request(
    symbol: str,
    candles: list[Candle],
    strategy: StrategyConfig,
    initial_cash: float,
    order_size: int,
    commission_pct: float,
    slippage_pct: float,
) -> BacktestRequest:
    return BacktestRequest(
        symbol=symbol,
        candles=candles,
        strategy=strategy,
        initial_cash=initial_cash,
        order_size=order_size,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
    )


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    index = int((len(values) - 1) * fraction)
    return values[index]


def _canonical_hash(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
