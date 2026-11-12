"""Risk evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RiskEvaluationMetrics:
    """Metrics for a risk evaluation."""

    evaluation_id: str
    timestamp: datetime
    intent_symbol: str
    intent_side: str
    intent_quantity: int
    approved: bool
    reasons: list[str] = field(default_factory=list)
    estimated_notional: float = 0.0
    estimated_risk_pct: float | None = None
    latency_ms: float = 0.0
    policy_version: str = "v1"
    actor: str = "system"


@dataclass(frozen=True, slots=True)
class RiskEngineMetrics:
    """Aggregated metrics for the risk engine."""

    total_evaluations: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    rejection_reasons: dict[str, int] = field(default_factory=dict)

    def record_evaluation(self, metrics: RiskEvaluationMetrics) -> None:
        """Record an evaluation."""
        self.total_evaluations += 1
        if metrics.approved:
            self.approved_count += 1
        else:
            self.rejected_count += 1

        self.total_latency_ms += metrics.latency_ms
        self.max_latency_ms = max(self.max_latency_ms, metrics.latency_ms)
        self.min_latency_ms = min(self.min_latency_ms, metrics.latency_ms)

        for reason in metrics.reasons:
            self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1

    @property
    def avg_latency_ms(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.total_latency_ms / self.total_evaluations

    @property
    def approval_rate(self) -> float:
        if self.total_evaluations == 0:
            return 0.0
        return self.approved_count / self.total_evaluations

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_evaluations": self.total_evaluations,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "approval_rate": self.approval_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "min_latency_ms": self.min_latency_ms if self.min_latency_ms != float("inf") else 0.0,
            "rejection_reasons": self.rejection_reasons,
        }