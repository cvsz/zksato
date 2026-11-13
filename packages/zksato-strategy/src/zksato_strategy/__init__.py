"""zksato-strategy: Strategies, indicators, backtesting, and research for zksato trading platform."""

from zksato_strategy.backtest import BacktestEngine
from zksato_strategy.hyperopt import HyperoptEngine
from zksato_strategy.indicators import (
    atr,
    bollinger_bands,
    bollinger_bands_series,
    ema,
    ema_series,
    highest,
    macd_series,
    rate_of_change,
    rsi,
    sma_series,
    stochastic_oscillator,
    vwap,
    williams_r,
)
from zksato_strategy.pairlist import PairListManager
from zksato_strategy.registry import PluginRegistry
from zksato_strategy.research import ResearchEngine
from zksato_strategy.research.memory import StrategyMemory
from zksato_strategy.strategies.classic import StrategyEngine
from zksato_strategy.trailing_stop import TrailingStop

__version__ = "2.0.0-dev"

__all__ = [
    # Backtest
    "BacktestEngine",
    # Hyperopt
    "HyperoptEngine",
    # Pairlist
    "PairListManager",
    # Registry
    "PluginRegistry",
    # Research
    "ResearchEngine",
    # Strategies
    "StrategyEngine",
    # Memory
    "StrategyMemory",
    # Trailing Stop
    "TrailingStop",
    "atr",
    "bollinger_bands",
    "bollinger_bands_series",
    "ema",
    "ema_series",
    "highest",
    "macd_series",
    "rate_of_change",
    # Indicators
    "rsi",
    "sma_series",
    "stochastic_oscillator",
    "vwap",
    "williams_r",
]
