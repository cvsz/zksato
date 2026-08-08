from zksato.config import Settings
from zksato.production import ExternalReadinessEvidence, ProductionReadinessService
from zksato.store import StateStore


def test_manual_canary_readiness_requires_all_external_and_runtime_gates() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://example.invalid/zksato",
        auth_required=True,
        session_secret="session-secret-that-is-long-enough",
        strict_reference_data=True,
        enforce_market_sessions=True,
        settrade_app_id="id",
        settrade_app_secret="secret",
        settrade_broker_id="broker",
        settrade_account_no="acct",
        settrade_pin="123456",
        account_allow_list="acct",
        live_requires_confirmation=True,
        require_distinct_approver=True,
        legacy_live_token_enabled=False,
    )
    store = StateStore()
    store.set_broker_reconciliation_ready(True)
    store.add_audit("test", "audit chain initialized")
    service = ProductionReadinessService(settings, store)
    evidence = ExternalReadinessEvidence(
        broker_permission_confirmed=True,
        legal_operational_review_complete=True,
        settrade_uat_complete=True,
        tls_verified=True,
        managed_secrets_verified=True,
        backup_restore_drill_complete=True,
        monitoring_alerts_verified=True,
        manual_canary_authorized=True,
        uat_orders_reconciled=1,
        evidence_reference="change-ticket-1",
    )
    report = service.report(evidence)
    assert report.ready_for_manual_canary is True
    plan = service.canary_plan(evidence)
    assert plan.allowed is True
    assert plan.autonomous_execution is False
    assert plan.maximum_orders == 1


def test_missing_external_evidence_fails_closed() -> None:
    service = ProductionReadinessService(Settings(), StateStore())
    report = service.report(ExternalReadinessEvidence())
    assert report.ready_for_manual_canary is False
