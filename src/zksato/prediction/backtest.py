from __future__ import annotations

from dataclasses import dataclass

from zksato.prediction.broker import PaperPredictionBroker, RiskRejected
from zksato.prediction.core import RiskLimits, Side, Tick
from zksato.prediction.strategy import ProbabilityEdgeStrategy


@dataclass(frozen=True)
class BacktestResult:
    pnl: float
    fills: int
    ending_cash: float
    winner: Side
    max_exposure: float


def run_backtest(ticks: list[Tick], starting_cash: float = 1_000.0, limits: RiskLimits | None = None) -> BacktestResult:
    if not ticks:
        raise ValueError("backtest requires at least one tick")
    limits = limits or RiskLimits()
    from zksato.config import Settings
    settings = Settings(prediction_enabled=True)
    broker = PaperPredictionBroker(settings=settings, limits=limits)
    broker.starting_cash = starting_cash
    broker.cash = starting_cash
    strategy = ProbabilityEdgeStrategy(limits.min_edge)
    max_exposure = 0.0
    for tick in ticks:
        signal = strategy.signal(tick)
        if signal is None:
            continue
        size = min(limits.max_order_usd, max(1.0, signal.edge * 100.0))
        try:
            broker.execute(signal.side, signal.market_price, size)
            max_exposure = max(max_exposure, broker.position.gross_exposure)
        except RiskRejected:
            continue
    winner = Side.UP if ticks[-1].spot >= ticks[-1].reference else Side.DOWN
    pnl = broker.settle(winner)
    return BacktestResult(pnl, len(broker.fills), broker.cash, winner, max_exposure)
