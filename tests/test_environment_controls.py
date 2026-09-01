import pytest
from fastapi.testclient import TestClient

from zksato import api as api_module
from zksato.api import app
from zksato.config import Settings
from zksato.domain import OrderIntent, OrderSubmission, Quote, RiskContext, Side
from zksato.production import ExternalReadinessEvidence, ProductionReadinessService
from zksato.service import RiskRejectedError, TradingModeError
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


@pytest.mark.asyncio
async def test_sandbox_mode_requires_settrade_credentials() -> None:
    settings = Settings(
        trading_mode="sandbox",
        settrade_app_id="",
        settrade_app_secret="",
        settrade_broker_id="",
        settrade_account_no="",
        settrade_pin="",
    )
    store = StateStore()
    store.update_quote(Quote(symbol="AOT", last=39.8, bid=39.7, offer=39.9))
    from zksato.broker.paper import PaperBroker
    from zksato.service import TradingService

    service = TradingService(settings, PaperBroker(store=store, initial_cash=500_000), store)
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
            client_order_id="sandbox-no-creds",
        ),
        risk=RiskContext(
            position_pct_after_trade=5.0,
            line_available=100_000.0,
            portfolio_value=500_000,
        ),
    )
    with pytest.raises(TradingModeError, match="credentials"):
        await service.submit(submission)


@pytest.mark.asyncio
async def test_paper_mode_does_not_require_settrade_credentials() -> None:
    settings = Settings(trading_mode="paper")
    store = StateStore()
    store.update_quote(Quote(symbol="AOT", last=39.8, bid=39.7, offer=39.9))
    from zksato.broker.paper import PaperBroker
    from zksato.service import TradingService

    service = TradingService(settings, PaperBroker(store=store, initial_cash=500_000), store)
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
            client_order_id="paper-no-creds",
        ),
        risk=RiskContext(
            position_pct_after_trade=5.0,
            line_available=100_000.0,
            portfolio_value=500_000,
        ),
    )
    record = await service.submit(submission)
    assert record.status.value in {"accepted", "filled"}


@pytest.mark.asyncio
async def test_live_mode_without_enabled_flag_blocks_orders() -> None:
    settings = Settings(
        trading_mode="live",
        live_trading_enabled=False,
        settrade_app_id="id",
        settrade_app_secret="secret",
        settrade_broker_id="broker",
        settrade_account_no="acct",
        settrade_pin="123456",
    )
    store = StateStore()
    store.update_quote(Quote(symbol="AOT", last=39.8, bid=39.7, offer=39.9))
    store.set_broker_reconciliation_ready(True)
    from zksato.broker.paper import PaperBroker
    from zksato.service import TradingService

    service = TradingService(settings, PaperBroker(store=store, initial_cash=500_000), store)
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
            client_order_id="live-not-enabled",
        ),
        risk=RiskContext(
            position_pct_after_trade=5.0,
            line_available=100_000.0,
            portfolio_value=500_000,
        ),
    )
    with pytest.raises(TradingModeError, match="live trading is disabled"):
        await service.submit(submission)


@pytest.mark.asyncio
async def test_live_mode_with_kill_switch_active_rejects_orders() -> None:
    settings = Settings(
        trading_mode="live",
        live_trading_enabled=True,
        kill_switch=True,
        settrade_app_id="id",
        settrade_app_secret="secret",
        settrade_broker_id="broker",
        settrade_account_no="acct",
        settrade_pin="123456",
    )
    store = StateStore()
    store.update_quote(Quote(symbol="AOT", last=39.8, bid=39.7, offer=39.9))
    from zksato.broker.paper import PaperBroker
    from zksato.service import TradingService

    service = TradingService(settings, PaperBroker(store=store, initial_cash=500_000), store)
    submission = OrderSubmission(
        intent=OrderIntent(
            symbol="AOT",
            side=Side.BUY,
            quantity=100,
            price=40.0,
            stop_loss=38.0,
            client_order_id="live-ks-active",
        ),
        risk=RiskContext(
            position_pct_after_trade=5.0,
            line_available=100_000.0,
            portfolio_value=500_000,
        ),
    )
    with pytest.raises(RiskRejectedError):
        await service.submit(submission)


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


def test_production_readiness_requires_complete_evidence() -> None:
    settings = Settings(
        environment="prod",
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
        broker_permission_confirmed=False,
        legal_operational_review_complete=False,
        settrade_uat_complete=False,
        tls_verified=False,
        managed_secrets_verified=False,
        backup_restore_drill_complete=False,
        monitoring_alerts_verified=False,
        incident_response_verified=False,
        deployment_rollback_verified=False,
        capacity_slo_verified=False,
        time_sync_verified=False,
        market_data_failover_verified=False,
        data_retention_verified=False,
        release_artifact_verified=False,
        manual_canary_authorized=False,
        uat_orders_reconciled=0,
        evidence_reference="",
    )
    report = service.report(evidence)
    assert report.ready_for_manual_canary is False
