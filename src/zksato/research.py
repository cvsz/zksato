from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from zksato.backtest import Backtester
from zksato.config import Settings
from zksato.domain import (
    BacktestRequest,
    BacktestResult,
    Bar,
    Candle,
    Signal,
    StrategyConfig,
    StrategyRun,
    StrategyVersion,
)
from zksato.market_rules import MarketSessionPolicy
from zksato.store import StateStore
from zksato.strategy import StrategyEngine
from zksato.video_ea_research import (
    StrategyRunEvidenceRequest,
    build_strategy_run_evidence,
)


class PromotionStage(StrEnum):
    RESEARCH = "research"
    PAPER = "paper"
    UAT = "uat"
    LIVE_MANUAL = "live_manual"


class WalkForwardRequest(BaseModel):
    symbol: str
    candles: list[Candle] = Field(min_length=20)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    initial_cash: float = Field(default=100_000, gt=0)
    order_size: int = Field(default=100, ge=1)
    commission_pct: float = Field(default=0.15, ge=0, le=5)
    slippage_pct: float = Field(default=0.05, ge=0, le=5)
    train_fraction: float = Field(default=0.7, gt=0.2, lt=0.9)
    strategy_version: str | None = Field(default=None, max_length=64)


class WalkForwardResult(BaseModel):
    symbol: str
    train: BacktestResult
    out_of_sample: BacktestResult
    approved_for_paper: bool
    reasons: list[str] = Field(default_factory=list)


class ReplayResult(BaseModel):
    symbol: str
    strategy: str
    bars_replayed: int
    signals: list[Signal]


class PromotionEvidence(BaseModel):
    strategy_name: str
    strategy_version: str
    requested_stage: PromotionStage
    total_trades: int = Field(ge=0)
    max_drawdown_pct: float = Field(ge=0)
    out_of_sample_return_pct: float
    paper_sessions: int = Field(default=0, ge=0)
    uat_orders_reconciled: int = Field(default=0, ge=0)
    operator_approved: bool = False


class PromotionDecision(BaseModel):
    approved: bool
    requested_stage: PromotionStage
    reasons: list[str] = Field(default_factory=list)
    requires_manual_live_confirmation: bool = True


class DriftRequest(BaseModel):
    expected_return_pct: float
    observed_return_pct: float
    tolerance_pct_points: float = Field(default=2.0, ge=0, le=100)


class DriftReport(BaseModel):
    expected_return_pct: float
    observed_return_pct: float
    drift_pct_points: float
    within_tolerance: bool


class ResearchService:
    """Deterministic research service that cannot submit broker orders."""

    def __init__(self, settings: Settings, store: StateStore) -> None:
        self.settings = settings
        self.store = store
        self.backtester = Backtester()
        self.strategy = StrategyEngine()
        self.market_sessions = MarketSessionPolicy(
            settings.market_timezone,
            settings.equity_sessions,
            settings.equity_holidays,
            settings.equity_special_sessions_json,
        )

    def register_strategy(
        self,
        name: str,
        version: str,
        config: StrategyConfig,
    ) -> StrategyVersion:
        canonical = json.dumps(
            config.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        record = StrategyVersion(
            name=name,
            version=version,
            config=config.model_dump(mode="json"),
            code_hash=hashlib.sha256(canonical.encode()).hexdigest(),
        )
        return self.store.add_strategy_version(record)

    def ingest_bars(self, bars: list[Bar]) -> int:
        for bar in bars:
            self.store.upsert_bar(bar)
        return len(bars)

    def _resolve_strategy_version(
        self,
        name: str,
        requested_version: str | None = None,
    ) -> StrategyVersion | None:
        versions = [item for item in self.store.list_strategy_versions() if item.name == name]
        if requested_version is not None:
            return next(
                (item for item in versions if item.version == requested_version),
                None,
            )
        return versions[0] if versions else None

    def _record_strategy_run(
        self,
        run: StrategyRun,
        version: StrategyVersion | None,
    ) -> None:
        evidence = build_strategy_run_evidence(StrategyRunEvidenceRequest(run=run, version=version))
        run.evidence_hash = evidence.evidence_hash
        self.store.add_strategy_run(run)

    def replay(
        self,
        symbol: str,
        strategy: StrategyConfig,
        *,
        timeframe: str = "1m",
    ) -> ReplayResult:
        bars = self.store.list_bars(symbol, timeframe=timeframe, limit=100_000)
        if self.settings.enforce_market_sessions:
            bars = [bar for bar in bars if self.market_sessions.state(bar.timestamp)[1]]
        prices: list[float] = []
        signals: list[Signal] = []
        for bar in bars:
            prices.append(bar.close)
            signal = self.strategy.evaluate(symbol.upper(), prices, strategy)
            if signal.action.value != "hold":
                signal.timestamp = bar.timestamp
                signals.append(signal)
        version = self._resolve_strategy_version(strategy.name)
        run = StrategyRun(
            strategy_version_id=version.id if version else None,
            strategy=strategy.name,
            symbol=symbol.upper(),
            mode="replay",
            inputs={
                "timeframe": timeframe,
                "bars": len(bars),
                "session_filter": self.settings.enforce_market_sessions,
            },
            output={"signals": len(signals)},
            completed_at=datetime.now(UTC),
        )
        self._record_strategy_run(run, version)
        return ReplayResult(
            symbol=symbol.upper(),
            strategy=strategy.name,
            bars_replayed=len(bars),
            signals=signals,
        )

    def walk_forward(self, request: WalkForwardRequest) -> WalkForwardResult:
        candles = request.candles
        if self.settings.enforce_market_sessions:
            candles = [
                candle
                for candle in request.candles
                if self.market_sessions.state(candle.timestamp)[1]
            ]
        if len(candles) < 20:
            raise ValueError("at least 20 in-session candles are required for walk-forward")
        split = max(
            5,
            min(
                len(candles) - 5,
                int(len(candles) * request.train_fraction),
            ),
        )
        train_request = BacktestRequest(
            symbol=request.symbol,
            candles=candles[:split],
            strategy=request.strategy,
            initial_cash=request.initial_cash,
            order_size=request.order_size,
            commission_pct=request.commission_pct,
            slippage_pct=request.slippage_pct,
        )
        test_request = train_request.model_copy(update={"candles": candles[split:]})
        train = self.backtester.run(train_request)
        out_of_sample = self.backtester.run(test_request)
        reasons: list[str] = []
        if out_of_sample.total_trades < self.settings.research_min_trades:
            reasons.append("out-of-sample trade count below promotion minimum")
        if out_of_sample.max_drawdown_pct > self.settings.research_max_drawdown_pct:
            reasons.append("out-of-sample drawdown exceeds promotion maximum")
        if out_of_sample.total_return_pct < self.settings.research_min_oos_return_pct:
            reasons.append("out-of-sample return below promotion minimum")
        version = self._resolve_strategy_version(
            request.strategy.name,
            request.strategy_version,
        )
        if request.strategy_version is not None and version is None:
            raise ValueError(
                f"strategy version {request.strategy.name}:{request.strategy_version} "
                "is not registered"
            )
        run = StrategyRun(
            strategy_version_id=version.id if version else None,
            strategy=request.strategy.name,
            symbol=request.symbol.upper(),
            mode="walk_forward",
            inputs={
                "train_bars": len(train_request.candles),
                "test_bars": len(test_request.candles),
                "commission_pct": request.commission_pct,
                "slippage_pct": request.slippage_pct,
                "session_filter": self.settings.enforce_market_sessions,
                "strategy_version": version.version if version else None,
            },
            output={
                "train_return_pct": train.total_return_pct,
                "oos_return_pct": out_of_sample.total_return_pct,
                "oos_drawdown_pct": out_of_sample.max_drawdown_pct,
                "approved_for_paper": not reasons,
            },
            completed_at=datetime.now(UTC),
        )
        self._record_strategy_run(run, version)
        return WalkForwardResult(
            symbol=request.symbol.upper(),
            train=train,
            out_of_sample=out_of_sample,
            approved_for_paper=not reasons,
            reasons=reasons,
        )

    def promotion_decision(self, evidence: PromotionEvidence) -> PromotionDecision:
        reasons: list[str] = []
        if evidence.total_trades < self.settings.research_min_trades:
            reasons.append("insufficient validated trades")
        if evidence.max_drawdown_pct > self.settings.research_max_drawdown_pct:
            reasons.append("drawdown exceeds promotion threshold")
        if evidence.out_of_sample_return_pct < self.settings.research_min_oos_return_pct:
            reasons.append("out-of-sample return below threshold")
        if (
            evidence.requested_stage in {PromotionStage.UAT, PromotionStage.LIVE_MANUAL}
            and evidence.paper_sessions < 1
        ):
            reasons.append("paper evidence is required before UAT")
        if evidence.requested_stage == PromotionStage.LIVE_MANUAL:
            if evidence.uat_orders_reconciled < 1:
                reasons.append("reconciled UAT evidence is required before live canary")
            if not evidence.operator_approved:
                reasons.append("explicit operator approval is required for live canary")
        return PromotionDecision(
            approved=not reasons,
            requested_stage=evidence.requested_stage,
            reasons=reasons,
            requires_manual_live_confirmation=True,
        )

    @staticmethod
    def drift_report(
        expected_return_pct: float,
        observed_return_pct: float,
        *,
        tolerance_pct_points: float = 2.0,
    ) -> DriftReport:
        drift = observed_return_pct - expected_return_pct
        return DriftReport(
            expected_return_pct=expected_return_pct,
            observed_return_pct=observed_return_pct,
            drift_pct_points=drift,
            within_tolerance=abs(drift) <= abs(tolerance_pct_points),
        )
