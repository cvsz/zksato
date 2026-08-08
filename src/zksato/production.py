from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from zksato.config import Settings
from zksato.store import StateStore


class ExternalReadinessEvidence(BaseModel):
    broker_permission_confirmed: bool = False
    legal_operational_review_complete: bool = False
    settrade_uat_complete: bool = False
    tls_verified: bool = False
    managed_secrets_verified: bool = False
    backup_restore_drill_complete: bool = False
    monitoring_alerts_verified: bool = False
    manual_canary_authorized: bool = False
    uat_orders_reconciled: int = Field(default=0, ge=0)
    evidence_reference: str | None = Field(default=None, max_length=512)


class ReadinessCheck(BaseModel):
    name: str
    passed: bool
    source: str
    detail: str


class ProductionReadinessReport(BaseModel):
    ready_for_manual_canary: bool
    checks: list[ReadinessCheck]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CanaryPlan(BaseModel):
    allowed: bool
    mode: str = "manual_confirmation_only"
    maximum_orders: int = 1
    autonomous_execution: bool = False
    required_controls: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ProductionReadinessService:
    """Evaluates rollout gates. It never submits an order or changes risk limits."""

    def __init__(self, settings: Settings, store: StateStore) -> None:
        self.settings = settings
        self.store = store

    def report(self, evidence: ExternalReadinessEvidence) -> ProductionReadinessReport:
        checks = [
            self._check(bool(self.settings.database_url), "durable PostgreSQL configured", "runtime"),
            self._check(self.settings.auth_required, "authentication/RBAC required", "runtime"),
            self._check(bool(self.settings.session_secret), "signed session secret configured", "runtime"),
            self._check(not self.settings.legacy_live_token_enabled, "legacy reusable live token disabled", "runtime"),
            self._check(self.settings.live_requires_confirmation, "live confirmation required", "runtime"),
            self._check(self.settings.require_distinct_approver, "four-eyes live approval enabled", "runtime"),
            self._check(self.settings.account_allowed, "configured account is allow-listed", "runtime"),
            self._check(self.settings.strict_reference_data, "strict equity reference data enabled", "runtime"),
            self._check(self.settings.enforce_market_sessions, "market-session enforcement enabled", "runtime"),
            self._check(self.settings.settrade_configured, "Settrade equity credentials configured", "runtime"),
            self._check(self.store.broker_reconciliation_ready(), "broker reconciliation converged", "runtime"),
            self._check(self.store.verify_audit_chain(), "audit hash chain verifies", "runtime"),
            self._check(evidence.broker_permission_confirmed, "broker permission confirmed", "external"),
            self._check(evidence.legal_operational_review_complete, "legal/operational review complete", "external"),
            self._check(evidence.settrade_uat_complete, "Settrade UAT evidence complete", "external"),
            self._check(evidence.uat_orders_reconciled > 0, "at least one UAT order reconciled", "external"),
            self._check(evidence.tls_verified, "TLS ingress verified", "external"),
            self._check(evidence.managed_secrets_verified, "managed secrets verified", "external"),
            self._check(evidence.backup_restore_drill_complete, "backup/restore drill complete", "external"),
            self._check(evidence.monitoring_alerts_verified, "monitoring and alerts verified", "external"),
            self._check(evidence.manual_canary_authorized, "manual canary explicitly authorized", "external"),
        ]
        return ProductionReadinessReport(
            ready_for_manual_canary=all(item.passed for item in checks),
            checks=checks,
        )

    def canary_plan(self, evidence: ExternalReadinessEvidence) -> CanaryPlan:
        report = self.report(evidence)
        reasons = [item.detail for item in report.checks if not item.passed]
        return CanaryPlan(
            allowed=report.ready_for_manual_canary,
            required_controls=[
                "one-time intent-bound approval",
                "distinct risk-admin and order-approver",
                "fresh trusted market data",
                "successful broker reconciliation",
                "kill switch verified",
                "single minimal-exposure manual order",
                "post-order fill/position reconciliation",
            ],
            reasons=reasons,
        )

    @staticmethod
    def _check(passed: bool, detail: str, source: str) -> ReadinessCheck:
        return ReadinessCheck(name=detail.replace(" ", "_"), passed=passed, source=source, detail=detail)
