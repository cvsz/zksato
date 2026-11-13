"""Hyperparameter optimization for strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import optuna

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

from zksato_core.models import Candle, StrategyConfig

from zksato_strategy.backtest import BacktestEngine


@dataclass
class HyperoptResult:
    """Result of hyperparameter optimization."""

    best_params: dict[str, Any]
    best_value: float
    n_trials: int
    study: Any = None


class HyperoptEngine:
    """Hyperparameter optimization using Optuna."""

    def __init__(
        self,
        candles: list[Candle],
        config: StrategyConfig,
        metric: str = "sharpe_ratio",
        n_trials: int = 100,
    ) -> None:
        if not OPTUNA_AVAILABLE:
            raise RuntimeError(
                "optuna is required for hyperparameter optimization. Install with: pip install optuna"
            )

        self.candles = candles
        self.config = config
        self.metric = metric
        self.n_trials = n_trials
        self.backtest_engine = BacktestEngine()

    def optimize(self, param_space: dict[str, tuple[Any, Any] | list[Any]]) -> HyperoptResult:
        """Run hyperparameter optimization."""

        def objective(trial: optuna.Trial) -> float:
            # Sample parameters
            params = {}
            for name, space in param_space.items():
                if isinstance(space, tuple) and len(space) == 2:
                    if isinstance(space[0], int):
                        params[name] = trial.suggest_int(name, space[0], space[1])
                    else:
                        params[name] = trial.suggest_float(name, space[0], space[1])
                elif isinstance(space, list):
                    params[name] = trial.suggest_categorical(name, space)

            # Create config with sampled parameters
            test_config = StrategyConfig(
                name=self.config.name,
                min_history=self.config.min_history,
                parameters=params,
            )

            # Run backtest
            result = self.backtest_engine.run(self.candles, test_config)

            # Return metric value
            metric_value = getattr(result, self.metric, 0.0)
            return metric_value if metric_value is not None else -999.0

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=self.n_trials)

        best_params = study.best_params
        best_value = study.best_value

        return HyperoptResult(
            best_params=best_params,
            best_value=best_value,
            n_trials=len(study.trials),
            study=study,
        )

    def get_best_config(self, result: HyperoptResult) -> StrategyConfig:
        """Create best config from optimization result."""
        return StrategyConfig(
            name=self.config.name,
            min_history=self.config.min_history,
            parameters=result.best_params,
        )
