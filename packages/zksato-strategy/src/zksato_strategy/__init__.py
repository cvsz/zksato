"""zksato-strategy: Strategies, indicators, backtesting, and research for zksato trading platform."""

from zksato_strategy.strategies.classic import StrategyEngine
from zksato_strategy.indicators import (
    rsi,
    ema,
    ema_series,
    sma_series,
    macd_series,
    bollinger_bands,
    bollinger_bands_series,
    atr,
    stochastic_oscillator,
    williams_r,
    vwap,
    rate_of_change,
    highest,
)
from zksato_strategy.backtest import BacktestEngine
from zksato_strategy.hyperopt import HyperoptEngine
from zksato_strategy.pairlist import PairListManager
from zksato_strategy.trailing_stop import TrailingStop
from zksato_strategy.research import ResearchEngine
from zksato_strategy.registry import PluginRegistry
from zksato_strategy.research.memory import StrategyMemory

__version__ = "2.0.0-dev"

__all__ = [
    # Strategies
    "StrategyEngine",
    # Indicators
    "rsi",
    "ema",
    "ema_series",
    "sma_series",
    "macd_series",
    "bollinger_bands",
    "bollinger_bands_series",
    "atr",
    "stochastic_oscillator",
    "williams_r",
    "vwap",
    "rate_of_change",
    "highest",
    # Backtest
    "BacktestEngine",
    # Hyperopt
    "HyperoptEngine",
    # Pairlist
    "PairListManager",
    # Trailing Stop
    "TrailingStop",
    # Research
    "ResearchEngine",
    # Registry
    "PluginRegistry",
    # Memory
    "StrategyMemory",
]