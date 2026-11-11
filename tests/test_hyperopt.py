"""
Test hyperopt functionality - parameter optimization for strategies.
"""
from __future__ import annotations

import datetime as dt

import pytest

from zksato.domain import Candle
from zksato.hyperopt import (
    LOSS_FUNCTIONS,
    HyperoptEngine,
    get_loss_function,
    run_hyperopt,
)
from zksato.strategy_freqtrade import strategy_registry


def test_get_loss_function():
    """Test getting loss functions by name."""
    loss_fn = get_loss_function("OnlyProfitHyperOptLoss")
    assert loss_fn.name == "OnlyProfitHyperOptLoss"
    assert loss_fn.direction == "minimize"

    loss_fn = get_loss_function("SharpeHyperOptLoss")
    assert loss_fn.name == "SharpeHyperOptLoss"


def test_get_loss_function_invalid():
    """Test getting unknown loss function raises ValueError."""
    try:
        get_loss_function("InvalidLossFunction")
        assert False, "Expected ValueError for invalid loss function"
    except ValueError:
        pass  # Expected


def test_list_loss_functions():
    """Test listing available loss functions."""
    loss_functions = {
        name: loss_func
        for name, loss_func in LOSS_FUNCTIONS.items()
    }
    assert "OnlyProfitHyperOptLoss" in loss_functions
    assert "SharpeHyperOptLoss" in loss_functions
    assert "SortinoHyperOptLoss" in loss_functions
    assert "CalmarHyperOptLoss" in loss_functions


def test_hyperopt_engine_initialization():
    """Test HyperoptEngine initialization."""
    # Build minimal candle data
    import datetime as dt

    candles = [
        Candle(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            symbol="AOT",
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        for _ in range(20)
    ]

    strategy_registry.get("ema_cross")
    engine = HyperoptEngine(
        strategy_class_name="ema_cross",
        symbol="AOT",
        candles=candles,
        loss_function_name="OnlyProfitHyperOptLoss",
        n_epochs=5,
    )
    assert engine.strategy_class is not None
    assert engine.symbol == "AOT"
    assert len(engine.candles) == 20
    assert engine.n_epochs == 5


def test_hyperopt_run():
    """Test running hyperopt optimization."""
    import datetime as dt

    candles = [
        Candle(
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            symbol="AOT",
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        for _ in range(30)
    ]

    result = run_hyperopt(
        strategy_class_name="ema_cross",
        symbol="AOT",
        candles=candles,
        loss_function_name="OnlyProfitHyperOptLoss",
        n_epochs=5,
    )
    assert result["best_trial"] is not None
    assert result["n_trials"] == 5
    assert result["loss_function"] == "OnlyProfitHyperOptLoss"

