"""Research engine for strategy development and analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from zksato_core.models import Candle, StrategyConfig
from zksato_strategy.backtest import BacktestEngine, BacktestResult
from zksato_strategy.strategies.classic import StrategyEngine


@dataclass
class ResearchNote:
    """A research note attached to a strategy."""
    strategy_id: str
    symbol: str
    timeframe: str
    note: str
    tags: list[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now(UTC)


@dataclass
class StrategyContext:
    """Persistent context for a strategy."""
    strategy_id: str
    symbol: str
    timeframe: str
    parameters: dict[str, Any]
    regime: str = "unknown"
    performance: dict[str, float] = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.performance is None:
            self.performance = {}
        if self.last_updated is None:
            self.last_updated = datetime.now(UTC)


class ResearchEngine:
    """Engine for strategy research and development."""
    
    def __init__(self) -> None:
        self.strategy_engine = StrategyEngine()
        self.backtest_engine = BacktestEngine()
        self._notes: list[ResearchNote] = []
        self._contexts: dict[str, StrategyContext] = {}
    
    def run_backtest(
        self,
        candles: list[Candle],
        config: StrategyConfig,
        sentiment_scores: list[float] | None = None,
    ) -> BacktestResult:
        """Run a backtest."""
        return self.backtest_engine.run(candles, config, sentiment_scores)
    
    def compare_strategies(
        self,
        candles: list[Candle],
        configs: list[StrategyConfig],
    ) -> dict[str, BacktestResult]:
        """Compare multiple strategies."""
        results = {}
        for config in configs:
            results[config.name] = self.backtest_engine.run(candles, config)
        return results
    
    def walk_forward_analysis(
        self,
        candles: list[Candle],
        config: StrategyConfig,
        train_window: int = 1000,
        test_window: int = 200,
        step: int = 100,
    ) -> list[dict[str, Any]]:
        """Walk-forward analysis."""
        results = []
        n = len(candles)
        
        for start in range(0, n - train_window - test_window, step):
            train_end = start + train_window
            test_end = train_end + test_window
            
            if test_end > n:
                break
            
            train_candles = candles[start:train_end]
            test_candles = candles[train_end:test_end]
            
            # Could optimize on train, test on test
            train_result = self.backtest_engine.run(train_candles, config)
            test_result = self.backtest_engine.run(test_candles, config)
            
            results.append({
                "train_start": start,
                "train_end": train_end,
                "test_end": test_end,
                "train_sharpe": train_result.sharpe_ratio,
                "test_sharpe": test_result.sharpe_ratio,
                "train_return": train_result.total_return_pct,
                "test_return": test_result.total_return_pct,
            })
        
        return results
    
    def parameter_stability(
        self,
        candles: list[Candle],
        config: StrategyConfig,
        param_ranges: dict[str, tuple],
        n_samples: int = 50,
    ) -> dict[str, Any]:
        """Test parameter stability."""
        import random
        
        base_result = self.backtest_engine.run(candles, config)
        base_sharpe = base_sharpe_ratio = base_result.sharpe_ratio or 0.0
        
        variations = []
        
        for _ in range(n_samples):
            # Randomly perturb parameters
            params = config.parameters.copy()
            for name, (min_val, max_val) in param_ranges.items():
                if name in params:
                    if isinstance(params[name], int):
                        params[name] = random.randint(int(min_val), int(max_val))
                    else:
                        params[name] = random.uniform(min_val, max_val)
            
            test_config = StrategyConfig(
                name=config.name,
                min_history=config.min_history,
                parameters=params,
            )
            
            result = self.backtest_engine.run(candles, test_config)
            variations.append({
                "params": params,
                "sharpe": result.sharpe_ratio or 0.0,
                "return": result.total_return_pct,
            })
        
        # Calculate stability metrics
        sharpes = [v["sharpe"] for v in variations]
        returns = [v["return"] for v in variations]
        
        import numpy as np
        
        return {
            "base_sharpe": base_sharpe,
            "mean_sharpe": np.mean(sharpes),
            "std_sharpe": np.std(sharpes),
            "min_sharpe": np.min(sharpes),
            "max_sharpe": np.max(sharpes),
            "sharpe_sharpe_ratio": np.mean(sharpes) / np.std(sharpes) if np.std(sharpes) > 0 else 0,
            "base_return": base_result.total_return_pct,
            "mean_return": np.mean(returns),
            "std_return": np.std(returns),
            "stability_score": 1 - (np.std(sharpes) / (abs(np.mean(sharpes)) + 1e-6)),
            "variations": variations,
        }
    
    def save_note(self, note: ResearchNote) -> None:
        """Save a research note."""
        self._notes.append(note)
    
    def get_notes(self, strategy_id: str | None = None, symbol: str | None = None) -> list[ResearchNote]:
        """Get research notes."""
        notes = self._notes
        if strategy_id:
            notes = [n for n in notes if n.strategy_id == strategy_id]
        if symbol:
            notes = [n for n in notes if n.symbol == symbol]
        return notes
    
    def save_context(self, context: StrategyContext) -> None:
        """Save strategy context."""
        self._contexts[context.strategy_id] = context
    
    def load_context(self, strategy_id: str) -> StrategyContext | None:
        """Load strategy context."""
        return self._contexts.get(strategy_id)
    
    def detect_regime(self, candles: list[Candle], lookback: int = 100) -> str:
        """Detect market regime."""
        if len(candles) < lookback:
            return "unknown"
        
        recent = candles[-lookback:]
        prices = [c.close for c in recent]
        
        # Simple regime detection based on trend and volatility
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        import numpy as np
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if mean_return > 0.001 and std_return < 0.02:
            return "bull_quiet"
        elif mean_return > 0.001 and std_return >= 0.02:
            return "bull_volatile"
        elif mean_return < -0.001 and std_return < 0.02:
            return "bear_quiet"
        elif mean_return < -0.001 and std_return >= 0.02:
            return "bear_volatile"
        else:
            return "sideways"