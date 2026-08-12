from zksato.config import Settings
from zksato.production import ExternalReadinessEvidence, ProductionReadinessService
from zksato.store import StateStore


def ready_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "prod",
        "trading_mode": "live",
        "live_trading_enabled": True,
        "database_url": "postgresql+psycopg://example.invalid/zksato",
        "redis_url": "redis://example.invalid/0",
        "auth_required": True,
        "api_keys": "operator-key:risk_admin",
        "session_secret": "session-secret-that-is-long-enough",
        "allowed_hosts": "trade.example.com",
        "strict_reference_data": True,
        "enforce_market_sessions": True,
        "settrade_app_id": "id",
        "settrade_app_secret": "secret",
        "settrade_broker_id": "broker",
        "settrade_account_no": "acct",
        "settrade_pin": "123456",
        "account_allow_list": "acct",
        "live_requires_confirmation": True,
        "require_distinct_approver": True,
        "legacy_live_token_enabled": False,
        "kill_switch": False,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def ready_evidence(**overrides: object) -> ExternalReadinessEvidence:
    values: dict[str, object] = {
        "broker_permission_confirmed": True,
        "legal_operational_review_complete": True,
        "settrade_uat_complete": True,
        "tls_verified": True,
        "managed_secrets_verified": True,
        "backup_restore_drill_complete": True,
        "monitoring_alerts_verified": True,
        "incident_response_verified": True,
        "deployment_rollback_verified": True,
        "capacity_slo_verified": True,
        "time_sync_verified": True,
        "market_data_failover_verified": True,
        "data_retention_verified": True,
        "release_artifact_verified": True,
        "manual_canary_authorized": True,
        "uat_orders_reconciled": 1,
        "evidence_reference": "change-ticket-1",
    }
    values.update(overrides)
    return ExternalReadinessEvidence(**values)  # type: ignore[arg-type]


def ready_store() -> StateStore:
    store = StateStore()
    store.set_broker_reconciliation_ready(True)
    store.add_audit("test", "audit chain initialized")
    return store


def test_manual_canary_readiness_requires_all_external_and_runtime_gates() -> None:
    service = ProductionReadinessService(ready_settings(), ready_store())
    evidence = ready_evidence()
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


def test_empty_account_allowlist_never_passes_production_readiness() -> None:
    service = ProductionReadinessService(ready_settings(account_allow_list=""), ready_store())
    report = service.report(ready_evidence())
    assert report.ready_for_manual_canary is False
    assert any(
        check.detail == "configured account is explicitly allow-listed" and not check.passed
        for check in report.checks
    )


def test_kill_switch_blocks_manual_canary_readiness() -> None:
    service = ProductionReadinessService(ready_settings(kill_switch=True), ready_store())
    report = service.report(ready_evidence())
    assert report.ready_for_manual_canary is False
    assert any(
        check.detail == "kill switch is clear before the separately authorized canary"
        and not check.passed
        for check in report.checks
    )


def test_runtime_must_explicitly_select_production_live_mode() -> None:
    for setting, value in (
        ("environment", "dev"),
        ("trading_mode", "paper"),
        ("live_trading_enabled", False),
        ("redis_url", None),
        ("api_keys", ""),
        ("allowed_hosts", ""),
    ):
        service = ProductionReadinessService(ready_settings(**{setting: value}), ready_store())
        assert service.report(ready_evidence()).ready_for_manual_canary is False
