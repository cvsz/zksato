"""
Hyperopt system for strategy parameter optimization.

This module provides Optuna-based hyperparameter optimization for trading
strategies, inspired by Freqtrade's hyperopt system. All optimization is
advisory/research only — optimized parameters are applied to strategy
instances, but order execution always routes through RiskEngine.

Supported parameter types:
- IntParameter: integer search space
- DecimalParameter: floating-point search space
- CategoricalParameter: discrete choices
- BooleanParameter: true/false

Supported loss functions:
- SharpeHyperOptLoss
- SortinoHyperOptLoss
- CalmarHyperOptLoss
- MaxDrawDownHyperOptLoss
- ProfitDrawDownHyperOptLoss
- OnlyProfitHyperOptLoss
- ShortTradeDurHyperOptLoss
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import optuna
from optuna.trial import Trial

from zksato.backtest_enhanced import EnhancedBacktester
from zksato.strategy_freqtrade import (
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
    Parameter,
    strategy_registry,
)

logger = logging.getLogger(__name__)


# ── Loss Functions ─────────────────────────────────────────────────────────


class LossDirection(StrEnum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class BaseHyperOptLoss(ABC):
    """Base class for hyperopt loss functions."""

    name: str = "BaseHyperOptLoss"
    direction: LossDirection = LossDirection.MINIMIZE

    @abstractmethod
    def __call__(
        self,
        results: dict[str, Any],
    ) -> float:
        """Calculate the loss value from backtest results.

        Lower values are better (when direction is MINIMIZE).
        """
        ...


class OnlyProfitHyperOptLoss(BaseHyperOptLoss):
    """Minimize negative profit (maximize profit)."""

    name = "OnlyProfitHyperOptLoss"
    direction = LossDirection.MINIMIZE

    def __call__(self, results: dict[str, Any]) -> float:
        metrics = results.get("metrics", {})
        total_profit_pct = getattr(metrics, "total_profit_pct", 0.0) or 0.0
        return -total_profit_pct


class SharpeHyperOptLoss(BaseHyperOptLoss):
    """Minimize negative Sharpe ratio."""

    name = "SharpeHyperOptLoss"
    direction = LossDirection.MINIMIZE

    def __call__(self, results: dict[str, Any]) -> float:
        metrics = results.get("metrics", {})
        sharpe = getattr(metrics, "sharpe_closed", 0.0) or 0.0
        return -sharpe


class SharpeHyperOptLossDaily(BaseHyperOptLoss):
    """Minimize negative daily Sharpe ratio."""

    name = "SharpeHyperOptLossDaily"
    direction = LossDirection.MINIMIZE

    def __call__(self, results: dict[str, Any]) -> float:
        metrics = results.get("metrics", {})
        sharpe = getattr(metrics, "sharpe_closed", 0.0) or 0.0
        return -sharpe


class SortinoHyperOptLoss(BaseHyperOptLoss):
    """Minimize negative Sortino ratio."""

    name = "SortinoHyperOptLoss"
    direction = LossDirection.MINIMIZE

    def __call__(self, results: dict[str, Any]) -> float:
        metrics = results.get("metrics", {})
        sortino = getattr(metrics, "sortino_closed", 0.0) or 0.0
        return -sortino


class CalmarHyperOptLoss(BaseHyperOptLoss):
    """Minimize negative Calmar ratio."""

    name = "CalmarHyperOptLoss"
    direction = LossDirection.MINIMIZE

    def __call__(self, results: dict[str, Any]) -> float:
        metrics = results.get("metrics", {})
        calmar = getattr(metrics, "calmar_closed", 0.0) or 0.0
        return -calmar


class MaxDrawDownHyperOptLoss(BaseHyperOptLoss):
    """Minimize maximum drawdown."""

    name = "MaxDrawDownHyperOptLoss"
    direction = LossDirection.MINIMIZE

    def __call__(self, results: dict[str, Any]) -> float:
        metrics = results.get("metrics", {})
        dd_pct = getattr(metrics, "absolute_drawdown_pct", 0.0) or 0.0
        return dd_pct


class MaxDrawDownRelativeHyperOptLoss(BaseHyperOptLoss):
    """Minimize both max drawdown and profit/drawdown ratio."""

    name = "MaxDrawDownRelativeHyperOptLoss"
    direction = LossDirection.MINIMIZE

    def __call__(self, results: dict[str, Any]) -> float:
        metrics = results.get("metrics", {})
        dd_pct = getattr(metrics, "absolute_drawdown_pct", 0.0) or 0.0
        profit_pct = getattr(metrics, "total_profit_pct", 0.0) or 0.0
        if dd_pct > 0:
            return dd_pct / (profit_pct + 1e-6)
        return dd_pct


class ProfitDrawDownHyperOptLoss(BaseHyperOptLoss):
    """Optimize profit vs drawdown tradeoff."""

    name = "ProfitDrawDownHyperOptLoss"
    direction = LossDirection.MINIMIZE

    def __init__(self, drawdown_multiplier: float = 1.0) -> None:
        self.drawdown_multiplier = drawdown_multiplier

    def __call__(self, results: dict[str, Any]) -> float:
        metrics = results.get("metrics", {})
        profit_pct = getattr(metrics, "total_profit_pct", 0.0) or 0.0
        dd_pct = getattr(metrics, "absolute_drawdown_pct", 0.0) or 0.0
        return -(profit_pct - self.drawdown_multiplier * dd_pct)


class ShortTradeDurHyperOptLoss(BaseHyperOptLoss):
    """Minimize trade duration (legacy Freqtrade default)."""

    name = "ShortTradeDurHyperOptLoss"
    direction = LossDirection.MINIMIZE

    def __call__(self, results: dict[str, Any]) -> float:
        trades = results.get("trades", [])
        if not trades:
            return 0.0
        total_duration = sum(t.duration_seconds for t in trades if t.duration_seconds is not None)
        return total_duration / len(trades) if trades else 0.0


# Loss function registry
LOSS_FUNCTIONS: dict[str, type[BaseHyperOptLoss]] = {
    "OnlyProfitHyperOptLoss": OnlyProfitHyperOptLoss,
    "SharpeHyperOptLoss": SharpeHyperOptLoss,
    "SharpeHyperOptLossDaily": SharpeHyperOptLossDaily,
    "SortinoHyperOptLoss": SortinoHyperOptLoss,
    "CalmarHyperOptLoss": CalmarHyperOptLoss,
    "MaxDrawDownHyperOptLoss": MaxDrawDownHyperOptLoss,
    "MaxDrawDownRelativeHyperOptLoss": MaxDrawDownRelativeHyperOptLoss,
    "ProfitDrawDownHyperOptLoss": ProfitDrawDownHyperOptLoss,
    "ShortTradeDurHyperOptLoss": ShortTradeDurHyperOptLoss,
}


def get_loss_function(name: str) -> BaseHyperOptLoss:
    """Get a loss function instance by name."""
    loss_class = LOSS_FUNCTIONS.get(name)
    if loss_class is None:
        raise ValueError(f"Unknown loss function: {name}")
    return loss_class()


# ── Hyperopt Trial ─────────────────────────────────────────────────────────


@dataclass
class HyperoptTrial:
    """Result of a single hyperopt trial."""

    epoch: int
    params: dict[str, Any]
    loss: float
    metrics: dict[str, Any]
    trades: list[Any] = field(default_factory=list)


@dataclass
class HyperoptResult:
    """Result of a hyperopt run."""

    best_trial: HyperoptTrial | None
    all_trials: list[HyperoptTrial]
    n_epochs: int
    loss_function: str
    strategy_name: str
    symbol: str
    timeframe: str


# ── Hyperopt Engine ────────────────────────────────────────────────────────


class HyperoptEngine:
    """Optuna-based hyperparameter optimization engine."""

    def __init__(
        self,
        strategy_class: type[IStrategy],
        symbol: str,
        candles: list[Any],
        loss_function_name: str = "OnlyProfitHyperOptLoss",
        n_epochs: int = 100,
        timeout: float | None = None,
        seed: int | None = None,
        spaces: list[str] | None = None,
    ) -> None:
        if optuna is None:
            raise ImportError("optuna is required for hyperopt. Install with: pip install optuna")

        self.strategy_class = strategy_class
        self.symbol = symbol
        self.candles = candles
        self.loss_function = get_loss_function(loss_function_name)
        self.n_epochs = n_epochs
        self.timeout = timeout
        self.seed = seed
        self.spaces = spaces  # None means all spaces

        self.backtester = EnhancedBacktester()
        self.trials: list[HyperoptTrial] = []
        self._trial_counter = 0

    def run(self) -> HyperoptResult:
        """Execute hyperopt optimization."""
        strategy_name = self.strategy_class.name
        logger.info(
            "Starting hyperopt: strategy=%s, symbol=%s, epochs=%d, loss=%s",
            strategy_name,
            self.symbol,
            self.n_epochs,
            self.loss_function.name,
        )

        sampler = optuna.samplers.TPESampler(seed=self.seed)
        study = optuna.create_study(
            direction=self.loss_function.direction.value,
            sampler=sampler,
        )

        study.optimize(
            self._objective,
            n_trials=self.n_epochs,
            timeout=self.timeout,
            gc_after_trial=True,
        )

        best_trial = self._get_best_trial()
        result = HyperoptResult(
            best_trial=best_trial,
            all_trials=list(self.trials),
            n_epochs=self.n_epochs,
            loss_function=self.loss_function.name,
            strategy_name=strategy_name,
            symbol=self.symbol,
            timeframe=self.strategy_class.timeframe,
        )

        logger.info(
            "Hyperopt complete: best loss=%.4f, best params=%s",
            best_trial.loss if best_trial else 0.0,
            best_trial.params if best_trial else {},
        )
        return result

    def _objective(self, trial: Trial) -> float:
        """Optuna objective function."""
        self._trial_counter += 1
        epoch = self._trial_counter

        # Suggest parameters for each hyperoptable parameter
        suggested_params: dict[str, Any] = {}
        for name, param in self.strategy_class().hyperopt_params.items():
            if self.spaces is not None and param.space not in self.spaces:
                continue

            suggested = self._suggest_param(trial, name, param)
            suggested_params[name] = suggested

        # Create strategy instance with suggested parameters
        strategy = self.strategy_class(config={})
        for name, value in suggested_params.items():
            strategy.set_hyperopt_param(name, value)

        # Run backtest
        try:
            backtest_result = self.backtester.run(
                symbol=self.symbol,
                candles=self.candles,
                signals=None,  # Strategy generates signals via populate_entry_trend
                strategy_name=self.strategy_class.name,
            )
        except Exception as exc:  # pragma: no cover - backtest failures
            logger.warning("Backtest failed for trial %d: %s", epoch, exc)
            return (
                float("inf")
                if self.loss_function.direction == LossDirection.MINIMIZE
                else float("-inf")
            )

        metrics = backtest_result.get("metrics", {})
        loss = self.loss_function(backtest_result)

        trial_result = HyperoptTrial(
            epoch=epoch,
            params=dict(suggested_params),
            loss=loss,
            metrics=metrics,
            trades=backtest_result.get("trades", []),
        )
        self.trials.append(trial_result)

        return loss

    def _suggest_param(
        self,
        trial: Trial,
        name: str,
        param: Parameter,
    ) -> Any:
        """Suggest a parameter value using Optuna."""
        if isinstance(param, IntParameter):
            return trial.suggest_int(name, param.low, param.high)
        elif isinstance(param, DecimalParameter):
            return trial.suggest_float(
                name,
                param.low,
                param.high,
                step=10**-param.decimals,
            )
        elif isinstance(param, CategoricalParameter):
            return trial.suggest_categorical(name, param.categories)
        elif isinstance(param, BooleanParameter):
            return trial.suggest_categorical(name, [True, False])
        else:
            return param.default

    def _get_best_trial(self) -> HyperoptTrial | None:
        """Get the trial with the best loss value."""
        if not self.trials:
            return None
        if self.loss_function.direction == LossDirection.MINIMIZE:
            return min(self.trials, key=lambda t: t.loss)
        return max(self.trials, key=lambda t: t.loss)


def run_hyperopt(
    strategy_name: str,
    symbol: str,
    candles: list[Any],
    loss_function: str = "OnlyProfitHyperOptLoss",
    n_epochs: int = 100,
    timeout: float | None = None,
    seed: int | None = None,
    spaces: list[str] | None = None,
) -> HyperoptResult:
    """Convenience function to run hyperopt on a registered strategy."""
    strategy_class = strategy_registry.get(strategy_name)
    if strategy_class is None:
        raise ValueError(f"Strategy '{strategy_name}' not registered")

    engine = HyperoptEngine(
        strategy_class=strategy_class,
        symbol=symbol,
        candles=candles,
        loss_function_name=loss_function,
        n_epochs=n_epochs,
        timeout=timeout,
        seed=seed,
        spaces=spaces,
    )
    return engine.run()
