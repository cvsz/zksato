from datetime import UTC, datetime, timedelta

from zksato.config import Settings
from zksato.domain import Bar, Candle, StrategyConfig
from zksato.research import (
    PromotionEvidence,
    PromotionStage,
    ResearchService,
    WalkForwardRequest,
)
from zksato.store import StateStore


def candles(count: int = 40) -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            timestamp=start + timedelta(minutes=index),
            open=100 + index * 0.1,
            high=101 + index * 0.1,
            low=99 + index * 0.1,
            close=100 + index * 0.1,
            volume=1000 + index,
        )
        for index in range(count)
    ]


def test_replay_and_walk_forward_are_deterministic() -> None:
    settings = Settings(research_min_trades=0 + 1, research_max_drawdown_pct=100)
    store = StateStore()
    service = ResearchService(settings, store)
    rows = [
        Bar(
            symbol="AOT",
            timestamp=item.timestamp,
            open=item.open,
            high=item.high,
            low=item.low,
            close=item.close,
            volume=item.volume,
            source="test",
        )
        for item in candles()
    ]
    assert service.ingest_bars(rows) == 40
    replay = service.replay("AOT", StrategyConfig(min_history=5, fast_period=2, slow_period=3))
    assert replay.bars_replayed == 40

    result = service.walk_forward(
        WalkForwardRequest(
            symbol="AOT",
            candles=candles(),
            strategy=StrategyConfig(min_history=5, fast_period=2, slow_period=3),
            train_fraction=0.7,
        )
    )
    assert result.symbol == "AOT"
    assert len(result.train.equity_curve) > 0
    assert len(result.out_of_sample.equity_curve) > 0


def test_live_promotion_requires_uat_and_operator_evidence() -> None:
    service = ResearchService(Settings(research_min_trades=1), StateStore())
    decision = service.promotion_decision(
        PromotionEvidence(
            strategy_name="ema_cross",
            strategy_version="1",
            requested_stage=PromotionStage.LIVE_MANUAL,
            total_trades=10,
            max_drawdown_pct=1,
            out_of_sample_return_pct=1,
            paper_sessions=1,
            uat_orders_reconciled=0,
            operator_approved=False,
        )
    )
    assert decision.approved is False
    assert decision.requires_manual_live_confirmation is True
