import pytest
from fastapi.testclient import TestClient

from zksato import api as api_module
from zksato.api import app
from zksato.config import Settings
from zksato.production import ExternalReadinessEvidence, ProductionReadinessService
from zksato.store import StateStore

client = TestClient(app)


def test_live_approvals_require_live_mode_even_with_valid_evidence() -> None:
    response = client.post(
        "/v1/live-approvals",
        json={
            "intent": {
                "symbol": "AOT",
                "side": "buy",
                "quantity": 100,
                "price": 40.0,
                "stop_loss": 38.0,
                "client_order_id": "la-1",
            }
        },
    )
    assert response.status_code == 409
    assert "live approvals are only valid in live mode" in response.json()["detail"]


def test_tfex_uat_endpoint_rejects_non_sandbox_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    for mode in ("paper", "live"):
        monkeypatch.setattr(api_module, "settings", Settings(trading_mode=mode))
        response = client.post(
            "/v1/tfex/orders/uat",
            json={
                "intent": {
                    "symbol": "BTCUSD",
                    "side": "LONG",
                    "position": "OPEN",
                    "volume": 1,
                    "price": 50000.0,
                }
            },
        )
        assert response.status_code == 409
        assert "UAT-only" in response.json()["detail"]


def test_production_readiness_fails_closed_in_non_prod_environments() -> None:
    for env in ("dev", "test", "uat"):
        settings = Settings(
            environment=env,
            trading_mode="live",
            live_trading_enabled=True,
            database_url="postgresql+psycopg://example.invalid/zksato",
            redis_url="redis://example.invalid/0",
            auth_required=True,
            api_keys="operator-key:risk_admin",
            session_secret="session-secret-that-is-long-enough",
            allowed_hosts="trade.example.com",
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
            kill_switch=False,
        )
        service = ProductionReadinessService(settings, StateStore())
        evidence = ExternalReadinessEvidence(
            broker_permission_confirmed=True,
            legal_operational_review_complete=True,
            settrade_uat_complete=True,
            tls_verified=True,
            managed_secrets_verified=True,
            backup_restore_drill_complete=True,
            monitoring_alerts_verified=True,
            incident_response_verified=True,
            deployment_rollback_verified=True,
            capacity_slo_verified=True,
            time_sync_verified=True,
            market_data_failover_verified=True,
            data_retention_verified=True,
            release_artifact_verified=True,
            manual_canary_authorized=True,
            uat_orders_reconciled=1,
            evidence_reference="change-ticket-1",
        )
        report = service.report(evidence)
        assert report.ready_for_manual_canary is False


def test_production_readiness_requires_prod_environment() -> None:
    settings = Settings(
        environment="prod",
        trading_mode="paper",
        live_trading_enabled=False,
        database_url="postgresql+psycopg://example.invalid/zksato",
        redis_url="redis://example.invalid/0",
        auth_required=True,
        api_keys="operator-key:risk_admin",
        session_secret="session-secret-that-is-long-enough",
        allowed_hosts="trade.example.com",
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
        kill_switch=False,
    )
    service = ProductionReadinessService(settings, StateStore())
    evidence = ExternalReadinessEvidence(
        broker_permission_confirmed=True,
        legal_operational_review_complete=True,
        settrade_uat_complete=True,
        tls_verified=True,
        managed_secrets_verified=True,
        backup_restore_drill_complete=True,
        monitoring_alerts_verified=True,
        incident_response_verified=True,
        deployment_rollback_verified=True,
        capacity_slo_verified=True,
        time_sync_verified=True,
        market_data_failover_verified=True,
        data_retention_verified=True,
        release_artifact_verified=True,
        manual_canary_authorized=True,
        uat_orders_reconciled=1,
        evidence_reference="change-ticket-1",
    )
    report = service.report(evidence)
    assert report.ready_for_manual_canary is False
