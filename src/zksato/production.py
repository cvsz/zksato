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
    incident_response_verified: bool = False
    deployment_rollback_verified: bool = False
    capacity_slo_verified: bool = False
    time_sync_verified: bool = False
    market_data_failover_verified: bool = False
    data_retention_verified: bool = False
    release_artifact_verified: bool = False
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
            self._check(
                self.settings.environment == "prod",
                "production environment selected",
                "runtime",
            ),
            self._check(
                self.settings.trading_mode == "live",
                "live trading mode selected for the manual canary",
                "runtime",
            ),
            self._check(
                self.settings.live_trading_enabled,
                "manual live trading explicitly enabled",
                "runtime",
            ),
            self._check(
                bool(self.settings.database_url),
                "durable PostgreSQL configured",
                "runtime",
            ),
            self._check(
                bool(self.settings.redis_url),
                "Redis coordination configured",
                "runtime",
            ),
            self._check(
                self.settings.auth_required,
                "authentication/RBAC required",
                "runtime",
            ),
            self._check(
                bool(self.settings.api_key_map),
                "at least one server-side operator credential configured",
                "runtime",
            ),
            self._check(
                bool(self.settings.session_secret),
                "signed session secret configured",
                "runtime",
            ),
            self._check(
                bool(self.settings.trusted_hosts),
                "trusted HTTP hosts explicitly configured",
                "runtime",
            ),
            self._check(
                not self.settings.legacy_live_token_enabled,
                "legacy reusable live token disabled",
                "runtime",
            ),
            self._check(
                self.settings.live_requires_confirmation,
                "live confirmation required",
                "runtime",
            ),
            self._check(
                self.settings.require_distinct_approver,
                "four-eyes live approval enabled",
                "runtime",
            ),
            self._check(
                bool(self.settings.allowed_accounts) and self.settings.account_allowed,
                "configured account is explicitly allow-listed",
                "runtime",
            ),
            self._check(
                self.settings.strict_reference_data,
                "strict equity reference data enabled",
                "runtime",
            ),
            self._check(
                self.settings.enforce_market_sessions,
                "market-session enforcement enabled",
                "runtime",
            ),
            self._check(
                self.settings.settrade_configured,
                "Settrade equity credentials configured",
                "runtime",
            ),
            self._check(
                not self.settings.kill_switch,
                "kill switch is clear before the separately authorized canary",
                "runtime",
            ),
            self._check(
                self.store.broker_reconciliation_ready(),
                "broker reconciliation converged",
                "runtime",
            ),
            self._check(
                self.store.verify_audit_chain(),
                "audit hash chain verifies",
                "runtime",
            ),
            self._check(
                evidence.broker_permission_confirmed,
                "broker permission confirmed",
                "external",
            ),
            self._check(
                evidence.legal_operational_review_complete,
                "legal/operational review complete",
                "external",
            ),
            self._check(
                evidence.settrade_uat_complete,
                "Settrade UAT evidence complete",
                "external",
            ),
            self._check(
                evidence.uat_orders_reconciled > 0,
                "at least one UAT order reconciled",
                "external",
            ),
            self._check(evidence.tls_verified, "TLS ingress verified", "external"),
            self._check(
                evidence.managed_secrets_verified,
                "managed secrets verified",
                "external",
            ),
            self._check(
                evidence.backup_restore_drill_complete,
                "backup/restore drill complete",
                "external",
            ),
            self._check(
                evidence.monitoring_alerts_verified,
                "monitoring and alerts verified",
                "external",
            ),
            self._check(
                evidence.incident_response_verified,
                "incident response and escalation path verified",
                "external",
            ),
            self._check(
                evidence.deployment_rollback_verified,
                "deployment rollback procedure verified",
                "external",
            ),
            self._check(
                evidence.capacity_slo_verified,
                "capacity and SLO evidence verified",
                "external",
            ),
            self._check(
                evidence.time_sync_verified,
                "host and application time synchronization verified",
                "external",
            ),
            self._check(
                evidence.market_data_failover_verified,
                "market-data disconnect and fail-closed recovery verified",
                "external",
            ),
            self._check(
                evidence.data_retention_verified,
                "audit and trading-data retention policy verified",
                "external",
            ),
            self._check(
                evidence.release_artifact_verified,
                "release artifact and immutable image digest verified",
                "external",
            ),
            self._check(
                evidence.manual_canary_authorized,
                "manual canary explicitly authorized",
                "external",
            ),
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
                "kill switch verified and immediately reachable",
                "single minimal-exposure manual order",
                "post-order fill/position reconciliation",
                "rollback and incident escalation ready",
            ],
            reasons=reasons,
        )

    @staticmethod
    def _check(passed: bool, detail: str, source: str) -> ReadinessCheck:
        return ReadinessCheck(
            name=detail.replace(" ", "_"),
            passed=passed,
            source=source,
            detail=detail,
        )
