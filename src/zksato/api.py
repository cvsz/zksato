from __future__ import annotations

from contextlib import asynccontextmanager
from threading import Lock, RLock
from time import monotonic
from typing import Annotated, Any

import httpx
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from zksato.agent_os import AgentExecutionEngine, AgentSubAccountManager
from zksato.approvals import ApprovalRepository, ApprovalRequest, LiveApproval
from zksato.auth import AuthManager, Principal, Role, require_roles
from zksato.automation import AutomationEngine
from zksato.backtest import Backtester
from zksato.broker.base import Broker
from zksato.broker.paper import PaperBroker
from zksato.broker.settrade import SettradeBroker
from zksato.config import get_settings
from zksato.coordination import CoordinationManager
from zksato.dashboard import DASHBOARD_HTML
from zksato.domain import (
    AccountSnapshot,
    AlertRule,
    BacktestRequest,
    BacktestResult,
    Bar,
    BotConfig,
    BotStatus,
    DashboardSnapshot,
    OrderIntent,
    OrderRecord,
    OrderStatus,
    OrderSubmission,
    PortfolioSnapshot,
    Quote,
    ReconciliationReport,
    RiskDecision,
    ScannerResult,
    Side,
    Signal,
    StrategyConfig,
    StrategyRun,
    StrategyVersion,
)
from zksato.market import DemoMarketFeed
from zksato.market.ccxt_feed import CcxtMarketFeed
from zksato.market.prediction_feed import PredictionMarketFeed
from zksato.market_settrade import SettradeRealtimeFeed
from zksato.market_terminal import router as market_terminal_router
from zksato.notifications import OutboxDispatcher, dispatch_telegram
from zksato.notifications.telegram import TelegramNotifier
from zksato.observability import (
    COORDINATION_HEALTH,
    HTTP_LATENCY,
    HTTP_REQUESTS,
    MARKET_FEED_AGE,
    OUTBOX_BACKLOG,
    bind_correlation_id,
    configure_logging,
    current_correlation_id,
    init_tracing,
    metrics_response,
    reset_correlation_id,
)
from zksato.persistence import build_store
from zksato.production import (
    CanaryPlan,
    ExternalReadinessEvidence,
    ProductionReadinessReport,
    ProductionReadinessService,
)
from zksato.reconcile import ReconciliationService, ReconciliationWorker
from zksato.research import (
    DriftReport,
    DriftRequest,
    PromotionDecision,
    PromotionEvidence,
    ReplayResult,
    ResearchService,
    WalkForwardRequest,
    WalkForwardResult,
)
from zksato.scanner import MarketScanner
from zksato.security import RateLimitMiddleware, SecurityHeadersMiddleware, redact_sensitive
from zksato.service import RiskRejectedError, TradingModeError, TradingService
from zksato.tfex import (
    SettradeTfexGateway,
    TfexContractMetadata,
    TfexOrderIntent,
    TfexOrderSubmission,
    TfexRiskDecision,
    TfexRiskEngine,
)
from zksato.tradingview import (
    TradingViewAlertParser,
    TradingViewConfigStore,
    TradingViewWebhookValidator,
)
from zksato.video_ea import VideoDerivedEaPlanner, VideoEaPlan, VideoEaPlanRequest
from zksato.video_ea_research import (
    BasketLifecycleMetrics,
    BasketLifecycleRequest,
    ExposureHeatmapRequest,
    ExposureHeatmapResult,
    MonteCarloTradeStressRequest,
    MonteCarloTradeStressResult,
    ParameterSweepRequest,
    ParameterSweepResult,
    RollingWalkForwardRequest,
    RollingWalkForwardResult,
    SensitivityRequest,
    SensitivityResult,
    VideoEaReplayRequest,
    VideoEaReplayResult,
    basket_lifecycle_metrics,
    max_exposure_heatmap,
    monte_carlo_trade_stress,
    parameter_sweep,
    replay_video_ea,
    rolling_walk_forward,
    sensitivity_analysis,
)
from zksato.video_ea_runtime import (
    VideoEaArmRequest,
    VideoEaCycleRuntime,
    VideoEaPriceObservation,
    VideoEaRuntimeControlResponse,
)

settings = get_settings()
configure_logging(settings.log_level, json_logs=settings.log_json)
init_tracing(settings.otel_service_name, settings.otel_endpoint)
store = build_store(settings)
approvals = ApprovalRepository(settings.database_url)
coordination = CoordinationManager(
    settings.redis_url,
    lock_ttl_seconds=settings.coordination_lock_ttl_seconds,
)
broker: Broker
if settings.trading_mode == "paper":
    broker = PaperBroker(
        store=store,
        initial_cash=settings.initial_cash,
        match_resting_limits=settings.paper_match_resting_limits,
        max_fill_quantity_per_quote=settings.paper_max_fill_quantity_per_quote,
        price_improvement=settings.paper_price_improvement,
    )
else:
    broker = SettradeBroker(settings=settings)
service = TradingService(
    settings=settings,
    broker=broker,
    store=store,
    approvals=approvals,
)
automation = AutomationEngine(settings=settings, store=store, service=service)
demo_feed = DemoMarketFeed(automation=automation)
ccxt_feed: CcxtMarketFeed | None = None
prediction_feed: PredictionMarketFeed | None = None
if settings.ccxt_configured and settings.trading_mode in {"paper", "sandbox"}:
    try:
        ccxt_feed = CcxtMarketFeed(automation=automation, settings=settings)
    except RuntimeError:
        ccxt_feed = None
if settings.prediction_enabled:
    try:
        prediction_feed = PredictionMarketFeed(settings=settings)
    except RuntimeError:
        prediction_feed = None
backtester = Backtester()
scanner = MarketScanner()
auth = AuthManager(settings)
reconciler = ReconciliationService(broker=broker, store=store, coordination=coordination)
reconciliation_worker = ReconciliationWorker(
    service=reconciler,
    interval_seconds=settings.reconciliation_interval_seconds,
)
outbox_dispatcher = OutboxDispatcher(
    store=store,
    webhook_url=settings.notification_webhook_url,
)
tradingview_validator = TradingViewWebhookValidator(settings.tradingview_webhook_secret)
tradingview_parser = TradingViewAlertParser()
tradingview_config = TradingViewConfigStore()
research = ResearchService(settings, store)
production = ProductionReadinessService(settings, store)
video_ea_planner = VideoDerivedEaPlanner()
video_ea_runtime_lock = RLock()
settrade_feed: SettradeRealtimeFeed | None = None
tfex_gateway: SettradeTfexGateway | None = None
tfex_gateway_lock = Lock()
settrade_feed_lock = Lock()
tfex_risk = TfexRiskEngine(settings)

read_access = require_roles(auth, Role.READ_ONLY)
strategy_access = require_roles(auth, Role.STRATEGY_OPERATOR)
order_access = require_roles(auth, Role.ORDER_APPROVER)
risk_access = require_roles(auth, Role.RISK_ADMIN)
auditor_access = require_roles(auth, Role.AUDITOR, Role.PLATFORM_ADMIN)
ReadPrincipal = Annotated[Principal, Depends(read_access)]
StrategyPrincipal = Annotated[Principal, Depends(strategy_access)]
OrderPrincipal = Annotated[Principal, Depends(order_access)]
RiskPrincipal = Annotated[Principal, Depends(risk_access)]
AuditorPrincipal = Annotated[Principal, Depends(auditor_access)]
LiveApprovalHeader = Annotated[str | None, Header(alias="X-Live-Approval-Id")]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.trading_mode != "paper" and settings.reconciliation_enabled:
        reconciliation_worker.start()
    outbox_dispatcher.start()
    if ccxt_feed is not None:
        ccxt_feed.start(["BTC", "ETH", "SOL", "BNB"])
    if prediction_feed is not None:
        prediction_feed.start(["BTC", "ETH", "SOL"])
    yield
    await reconciliation_worker.stop()
    await outbox_dispatcher.stop()
    if ccxt_feed is not None:
        await ccxt_feed.stop()
    if prediction_feed is not None:
        await prediction_feed.stop()
    if settrade_feed is not None:
        await settrade_feed.stop()
    await coordination.close()
    approvals.close()
    store.close()


app = FastAPI(
    title="zksato",
    version="1.0.0",
    description="Risk-first automated trading control plane with dashboard",
    lifespan=lifespan,
)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
    coordination=coordination,
)
app.add_middleware(SecurityHeadersMiddleware)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-CSRF-Token",
            "X-Live-Approval-Id",
            "X-Request-ID",
        ],
        allow_credentials=True,
    )
if settings.trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

app.include_router(market_terminal_router)


@app.middleware("http")
async def observe_http(request: Request, call_next):
    supplied = request.headers.get("X-Request-ID")
    correlation_id = supplied[:128] if supplied else None
    token = bind_correlation_id(correlation_id)
    started = monotonic()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = current_correlation_id()
        route = request.scope.get("route")
        route_name = getattr(route, "path", request.url.path)
        HTTP_REQUESTS.labels(
            method=request.method,
            route=route_name,
            status=str(response.status_code),
        ).inc()
        HTTP_LATENCY.labels(method=request.method, route=route_name).observe(monotonic() - started)
        return response
    finally:
        reset_correlation_id(token)


def _tfex_gateway() -> SettradeTfexGateway:
    global tfex_gateway
    if settings.trading_mode == "paper":
        raise HTTPException(status_code=409, detail="TFEX gateway requires sandbox/live mode")
    if not settings.settrade_tfex_configured:
        raise HTTPException(status_code=409, detail="Settrade TFEX credentials are incomplete")
    if tfex_gateway is None:
        with tfex_gateway_lock:
            if tfex_gateway is None:
                try:
                    tfex_gateway = SettradeTfexGateway(settings)
                except RuntimeError as exc:
                    raise HTTPException(status_code=409, detail=str(exc)) from exc
    return tfex_gateway


def _require_video_ea_paper_mode() -> None:
    if settings.trading_mode != "paper":
        raise HTTPException(
            status_code=409,
            detail="video EA operator controls are restricted to paper mode",
        )


def _video_ea_runtime_key(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 32:
        raise HTTPException(status_code=422, detail="invalid video EA symbol")
    return f"video-ea-cycle:{normalized}"


def _load_video_ea_runtime(symbol: str) -> VideoEaCycleRuntime:
    payload = store.get_runtime_state(_video_ea_runtime_key(symbol))
    if payload is None:
        return VideoEaCycleRuntime()
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=409, detail="video EA runtime snapshot is invalid")
    try:
        return VideoEaCycleRuntime.from_snapshot(snapshot)
    except ValueError as exc:
        store.add_audit(
            "video_ea.recovery_failed",
            f"video EA runtime recovery failed for {symbol.upper()}",
            {"symbol": symbol.upper(), "reason": str(exc)},
        )
        raise HTTPException(
            status_code=409,
            detail="video EA runtime recovery failed closed; operator reset is required",
        ) from exc


def _persist_video_ea_runtime(symbol: str, runtime: VideoEaCycleRuntime) -> None:
    store.save_runtime_state(
        _video_ea_runtime_key(symbol),
        {"snapshot": runtime.snapshot().model_dump(mode="json")},
    )


async def _health_payload() -> dict[str, object]:
    database_healthy = store.health()
    coordination_healthy = await coordination.health()
    COORDINATION_HEALTH.set(1 if coordination_healthy else 0)
    reconciliation_ready = (
        True
        if settings.trading_mode == "paper" or not settings.reconciliation_enabled
        else store.broker_reconciliation_ready()
    )
    quote_ages = [store.quote_age_seconds(item.symbol) for item in store.list_quotes()]
    usable_ages = [age for age in quote_ages if age is not None]
    if usable_ages:
        MARKET_FEED_AGE.set(min(usable_ages))
    OUTBOX_BACKLOG.set(len(store.pending_outbox(10_000)))
    audit_chain_valid = store.verify_audit_chain()
    healthy = (
        database_healthy and coordination_healthy and reconciliation_ready and audit_chain_valid
    )
    return {
        "status": "ok" if healthy else "degraded",
        "mode": settings.trading_mode,
        "automation": automation.status.state,
        "settrade_configured": settings.settrade_configured,
        "settrade_tfex_configured": settings.settrade_tfex_configured,
        "persistence": "sql" if settings.database_url else "memory",
        "persistence_healthy": database_healthy,
        "coordination": "redis" if settings.redis_url else "local",
        "coordination_healthy": coordination_healthy,
        "reconciliation_ready": reconciliation_ready,
        "audit_chain_valid": audit_chain_valid,
    }


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page() -> str:
    if not settings.dashboard_enabled:
        raise HTTPException(status_code=404, detail="dashboard disabled")
    return DASHBOARD_HTML


@app.get("/livez", include_in_schema=False)
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health")
async def health() -> dict[str, object]:
    return await _health_payload()


@app.get("/readyz", include_in_schema=False)
async def readiness() -> dict[str, object]:
    payload = await _health_payload()
    if payload["status"] != "ok":
        raise HTTPException(status_code=503, detail=payload)
    return payload


@app.get("/metrics", include_in_schema=False)
async def metrics(_principal: ReadPrincipal):
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="metrics disabled")
    return metrics_response()


@app.post("/v1/auth/session")
async def create_session(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> dict[str, object]:
    issued = auth.issue_session(authorization, x_api_key)
    response.set_cookie(
        settings.session_cookie_name,
        issued.token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.environment == "prod",
        samesite="strict",
        path="/",
    )
    return {
        "subject": issued.principal.subject,
        "role": issued.principal.role.value,
        "csrf_token": issued.csrf_token,
        "expires_at": issued.expires_at.isoformat(),
    }


@app.delete("/v1/auth/session")
async def delete_session(
    response: Response,
    _principal: ReadPrincipal,
    session_token: Annotated[
        str | None,
        Cookie(alias=settings.session_cookie_name),
    ] = None,
) -> dict[str, bool]:
    if session_token:
        auth.revoke_session(session_token)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"revoked": bool(session_token)}


@app.get("/v1/auth/me")
async def auth_me(principal: ReadPrincipal) -> dict[str, str]:
    return {
        "subject": principal.subject,
        "role": principal.role.value,
        "auth_method": principal.auth_method,
    }


@app.get("/v1/config")
async def config(_principal: ReadPrincipal) -> dict[str, object]:
    return {
        "environment": settings.environment,
        "trading_mode": settings.trading_mode,
        "live_trading_enabled": settings.live_trading_enabled,
        "live_requires_confirmation": settings.live_requires_confirmation,
        "require_distinct_approver": settings.require_distinct_approver,
        "automation_enabled": settings.automation_enabled,
        "auth_required": settings.auth_required,
        "persistence_enabled": bool(settings.database_url),
        "redis_enabled": bool(settings.redis_url),
        "settrade_configured": settings.settrade_configured,
        "settrade_tfex_configured": settings.settrade_tfex_configured,
        "reconciliation_ready": store.broker_reconciliation_ready(),
        "watchlist": settings.watchlist,
        "paper": {
            "match_resting_limits": settings.paper_match_resting_limits,
            "max_fill_quantity_per_quote": settings.paper_max_fill_quantity_per_quote,
            "price_improvement": settings.paper_price_improvement,
        },
        "market": {
            "timezone": settings.market_timezone,
            "sessions": settings.equity_sessions,
            "session_enforcement": settings.enforce_market_sessions,
            "configured_holidays": len(service.market_sessions.holidays),
            "special_session_dates": len(service.market_sessions.special_sessions),
        },
        "risk": {
            "kill_switch": settings.kill_switch,
            "max_positions": settings.max_positions,
            "max_position_pct": settings.max_position_pct,
            "max_risk_per_trade_pct": settings.max_risk_per_trade_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_drawdown_pct": settings.max_drawdown_pct,
            "max_orders_per_day": settings.max_orders_per_day,
            "max_open_orders": settings.max_open_orders,
            "max_notional_per_order": settings.max_notional_per_order,
            "max_gross_exposure_pct": settings.max_gross_exposure_pct,
            "max_net_exposure_pct": settings.max_net_exposure_pct,
            "max_symbol_exposure_pct": settings.max_symbol_exposure_pct,
            "max_sector_exposure_pct": settings.max_sector_exposure_pct,
            "market_data_stale_seconds": settings.market_data_stale_seconds,
            "enforce_market_sessions": settings.enforce_market_sessions,
            "strict_reference_data": settings.strict_reference_data,
            "require_stop_loss": settings.require_stop_loss,
            "max_tfex_contracts": settings.max_tfex_contracts,
            "max_tfex_margin_usage_pct": settings.max_tfex_margin_usage_pct,
        },
    }


@app.get("/v1/dashboard", response_model=DashboardSnapshot)
async def dashboard_snapshot(_principal: ReadPrincipal) -> DashboardSnapshot:
    return DashboardSnapshot(
        mode=settings.trading_mode,
        automation_enabled=settings.automation_enabled,
        kill_switch=settings.kill_switch,
        bot=automation.status,
        portfolio=await service.portfolio(),
        quotes=store.list_quotes(),
        orders=await service.list_orders(),
        signals=store.list_signals(100),
        alerts=store.list_alerts(),
        audit=store.list_audit(100),
    )


@app.get("/v1/reference/instruments")
async def reference_instruments(_principal: ReadPrincipal) -> list[dict[str, object]]:
    return [item.model_dump(mode="json") for item in service.instruments.list()]


@app.get("/v1/market/session")
async def market_session(_principal: ReadPrincipal) -> dict[str, object]:
    return service.market_sessions.explain()


@app.post("/v1/market/quote", response_model=Quote)
async def ingest_quote(quote: Quote, _principal: StrategyPrincipal) -> Quote:
    await automation.on_quote(quote)
    return quote


@app.get("/v1/market/quotes", response_model=list[Quote])
async def list_quotes(_principal: ReadPrincipal) -> list[Quote]:
    return store.list_quotes()


@app.get("/v1/market/history/{symbol}")
async def price_history(symbol: str, _principal: ReadPrincipal) -> dict[str, object]:
    return {"symbol": symbol.upper(), "prices": store.get_prices(symbol)}


@app.get("/v1/market/health/{symbol}")
async def market_health(symbol: str, _principal: ReadPrincipal) -> dict[str, object]:
    age = store.quote_age_seconds(symbol)
    return {
        "symbol": symbol.upper(),
        "quote_age_seconds": age,
        "stale": age is None or age > settings.market_data_stale_seconds,
    }


@app.get("/v1/scanner", response_model=list[ScannerResult])
async def scan_market(
    _principal: ReadPrincipal,
    min_volume: float = 0,
    min_abs_change_pct: float = 0,
    limit: int = 20,
) -> list[ScannerResult]:
    return scanner.scan(
        store.list_quotes(),
        min_volume=max(min_volume, 0),
        min_abs_change_pct=max(min_abs_change_pct, 0),
        limit=min(max(limit, 1), 200),
    )


@app.post("/v1/market/demo/start")
async def start_demo(_principal: StrategyPrincipal) -> dict[str, object]:
    if settings.trading_mode != "paper":
        raise HTTPException(status_code=409, detail="demo feed is only available in paper mode")
    demo_feed.start(settings.watchlist)
    store.add_audit("market.demo.started", "synthetic paper feed started")
    return {"running": True, "symbols": settings.watchlist}


@app.post("/v1/market/demo/stop")
async def stop_demo(_principal: StrategyPrincipal) -> dict[str, bool]:
    await demo_feed.stop()
    store.add_audit("market.demo.stopped", "synthetic paper feed stopped")
    return {"running": False}


@app.post("/v1/market/settrade/start")
async def start_settrade_feed(_principal: StrategyPrincipal) -> dict[str, object]:
    global settrade_feed
    if settings.trading_mode == "paper":
        raise HTTPException(status_code=409, detail="Settrade feed requires sandbox/live mode")
    with settrade_feed_lock:
        if settrade_feed is None:
            settrade_feed = SettradeRealtimeFeed(settings, automation)
        settrade_feed.start(settings.watchlist)
    store.add_audit("market.settrade.started", "Settrade realtime supervisor started")
    return settrade_feed.status()


@app.post("/v1/market/settrade/stop")
async def stop_settrade_feed(_principal: StrategyPrincipal) -> dict[str, object]:
    if settrade_feed is not None:
        await settrade_feed.stop()
    store.add_audit("market.settrade.stopped", "Settrade realtime supervisor stopped")
    return {"running": False}


@app.get("/v1/market/settrade/status")
async def settrade_feed_status(_principal: ReadPrincipal) -> dict[str, object]:
    if settrade_feed is None:
        return {"running": False, "connected": False, "symbols": []}
    return settrade_feed.status()


@app.post("/v1/bot/start", response_model=BotStatus)
async def start_bot(bot_config: BotConfig, _principal: StrategyPrincipal) -> BotStatus:
    if not settings.automation_enabled:
        raise HTTPException(status_code=409, detail="automation is disabled by server policy")
    if settings.trading_mode == "live" and bot_config.auto_execute:
        raise HTTPException(
            status_code=409,
            detail="autonomous live execution is disabled; use signal-only mode",
        )
    return automation.start(bot_config)


@app.post("/v1/bot/pause", response_model=BotStatus)
async def pause_bot(_principal: StrategyPrincipal) -> BotStatus:
    return automation.pause()


@app.post("/v1/bot/resume", response_model=BotStatus)
async def resume_bot(_principal: StrategyPrincipal) -> BotStatus:
    try:
        return automation.resume()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/bot/stop", response_model=BotStatus)
async def stop_bot(_principal: StrategyPrincipal) -> BotStatus:
    return automation.stop()


@app.post("/v1/bot/tick", response_model=BotStatus)
async def bot_tick(_principal: StrategyPrincipal) -> BotStatus:
    return await automation.tick()


@app.get("/v1/bot", response_model=BotStatus)
async def bot_status(_principal: ReadPrincipal) -> BotStatus:
    return automation.status


@app.post("/v1/risk/check", response_model=RiskDecision)
async def risk_check(submission: OrderSubmission, _principal: ReadPrincipal) -> RiskDecision:
    # Recompute trusted risk context server-side; do not trust client-supplied RiskContext
    context = await service.risk_context_for(submission.intent)
    return service.risk_engine.evaluate(submission.intent, context)


@app.post("/v1/risk/preflight", response_model=RiskDecision)
async def risk_preflight(intent: OrderIntent, _principal: ReadPrincipal) -> RiskDecision:
    context = await service.risk_context_for(intent)
    return service.risk_engine.evaluate(intent, context)


@app.post("/v1/live-approvals", response_model=LiveApproval, status_code=201)
async def create_live_approval(
    request: ApprovalRequest,
    principal: RiskPrincipal,
) -> LiveApproval:
    if settings.trading_mode != "live":
        raise HTTPException(status_code=409, detail="live approvals are only valid in live mode")
    context = await service.risk_context_for(request.intent)
    decision = service.risk_engine.evaluate(request.intent, context)
    if not decision.approved:
        raise HTTPException(status_code=422, detail=decision.model_dump())
    ttl = request.ttl_seconds or settings.live_approval_ttl_seconds
    approval = approvals.create(request.intent, created_by=principal.subject, ttl_seconds=ttl)
    store.add_audit(
        "live_approval.created",
        f"approval created for {request.intent.side.value} {request.intent.symbol}",
        {"approval_id": str(approval.id), "created_by": principal.subject},
    )
    return approval


@app.get("/v1/live-approvals", response_model=list[LiveApproval])
async def list_live_approvals(
    _principal: RiskPrincipal,
    limit: int = 100,
) -> list[LiveApproval]:
    return approvals.list_recent(min(max(limit, 1), 1000))


@app.post("/v1/orders", response_model=OrderRecord, status_code=201)
async def place_order(
    submission: OrderSubmission,
    principal: OrderPrincipal,
    approval_id: LiveApprovalHeader = None,
) -> OrderRecord:
    trusted_context = await service.risk_context_for(submission.intent)
    trusted_submission = submission.model_copy(update={"risk": trusted_context})
    try:
        return await service.submit(
            trusted_submission,
            automated=False,
            actor=principal.subject,
            approval_id=approval_id,
        )
    except RiskRejectedError as exc:
        raise HTTPException(status_code=422, detail=exc.decision.model_dump()) from exc
    except TradingModeError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/orders", response_model=list[OrderRecord])
async def list_orders(
    _principal: ReadPrincipal,
    symbol: str | None = None,
    status: OrderStatus | None = None,
    side: Side | None = None,
    limit: int = 500,
) -> list[OrderRecord]:
    return await service.list_orders(
        symbol=symbol,
        status=status,
        side=side,
        limit=min(max(limit, 1), 5000),
    )


@app.post("/v1/orders/cancel-open", response_model=list[OrderRecord])
async def cancel_open_orders(
    _principal: OrderPrincipal,
    symbol: str | None = None,
) -> list[OrderRecord]:
    try:
        return await service.cancel_open_orders(symbol)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/orders/{order_id}", response_model=OrderRecord)
async def get_order(order_id: str, _principal: ReadPrincipal) -> OrderRecord:
    try:
        return await service.get_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/v1/orders/{order_id}", response_model=OrderRecord)
async def cancel_order(order_id: str, _principal: OrderPrincipal) -> OrderRecord:
    try:
        return await service.cancel_order(order_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/order-events")
async def order_events(_principal: AuditorPrincipal, limit: int = 200) -> list[dict[str, object]]:
    return [
        item.model_dump(mode="json") for item in store.list_order_events(min(max(limit, 1), 2000))
    ]


@app.get("/v1/fills")
async def fills(_principal: AuditorPrincipal, limit: int = 200) -> list[dict[str, object]]:
    return [item.model_dump(mode="json") for item in store.list_fills(min(max(limit, 1), 2000))]


@app.get("/v1/risk/evaluations")
async def risk_evaluations(
    _principal: AuditorPrincipal,
    limit: int = 200,
) -> list[dict[str, object]]:
    return [
        item.model_dump(mode="json")
        for item in store.list_risk_evaluations(min(max(limit, 1), 2000))
    ]


@app.post("/v1/reconcile", response_model=ReconciliationReport)
async def reconcile_orders(_principal: OrderPrincipal) -> ReconciliationReport:
    try:
        return await reconciler.run()
    except (RuntimeError, OSError, ValueError) as exc:
        store.set_broker_reconciliation_ready(False)
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/portfolio", response_model=PortfolioSnapshot)
async def portfolio(_principal: ReadPrincipal) -> PortfolioSnapshot:
    return await service.portfolio()


@app.get("/v1/account-snapshots", response_model=list[AccountSnapshot])
async def account_snapshots(
    _principal: AuditorPrincipal,
    limit: int = 200,
) -> list[AccountSnapshot]:
    return store.list_account_snapshots(min(max(limit, 1), 2000))


@app.get("/v1/signals", response_model=list[Signal])
async def signals(_principal: ReadPrincipal, limit: int = 100) -> list[Signal]:
    return store.list_signals(min(max(limit, 1), 1000))


@app.post("/v1/alerts", response_model=AlertRule, status_code=201)
async def create_alert(alert: AlertRule, _principal: StrategyPrincipal) -> AlertRule:
    store.add_audit("alert.created", f"alert created for {alert.symbol}")
    return store.add_alert(alert)


@app.get("/v1/alerts", response_model=list[AlertRule])
async def list_alerts(_principal: ReadPrincipal) -> list[AlertRule]:
    return store.list_alerts()


@app.delete("/v1/alerts/{alert_id}")
async def delete_alert(alert_id: str, _principal: StrategyPrincipal) -> dict[str, bool]:
    return {"deleted": store.delete_alert(alert_id)}


@app.get("/v1/audit")
async def audit(_principal: AuditorPrincipal, limit: int = 100) -> list[dict[str, object]]:
    rows = [event.model_dump(mode="json") for event in store.list_audit(min(max(limit, 1), 1000))]
    return redact_sensitive(rows)


@app.get("/v1/audit/verify")
async def audit_verify(_principal: AuditorPrincipal) -> dict[str, bool]:
    return {"valid": store.verify_audit_chain()}


@app.post("/v1/backtest", response_model=BacktestResult)
async def backtest(request: BacktestRequest, _principal: ReadPrincipal) -> BacktestResult:
    try:
        result = backtester.run(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.add_audit(
        "backtest.completed",
        f"backtest {result.symbol}: {result.total_return_pct:.2f}%",
        {"trades": result.total_trades, "drawdown": result.max_drawdown_pct},
    )
    return result


@app.post("/v1/research/bars")
async def research_bars(bars: list[Bar], _principal: StrategyPrincipal) -> dict[str, int]:
    return {"stored": research.ingest_bars(bars)}


@app.get("/v1/research/bars/{symbol}", response_model=list[Bar])
async def research_list_bars(
    symbol: str,
    _principal: ReadPrincipal,
    timeframe: str = "1m",
    limit: int = 5000,
) -> list[Bar]:
    return store.list_bars(symbol, timeframe=timeframe, limit=min(max(limit, 1), 100_000))


@app.post("/v1/research/strategies/{name}/{version}", response_model=StrategyVersion)
async def register_strategy(
    name: str,
    version: str,
    config: StrategyConfig,
    _principal: StrategyPrincipal,
) -> StrategyVersion:
    record = research.register_strategy(name, version, config)
    store.add_audit(
        "research.strategy_registered",
        f"registered strategy {name}:{version}",
        {"code_hash": record.code_hash},
    )
    return record


@app.get("/v1/research/strategies", response_model=list[StrategyVersion])
async def research_strategies(_principal: ReadPrincipal) -> list[StrategyVersion]:
    return store.list_strategy_versions()


@app.get("/v1/research/runs", response_model=list[StrategyRun])
async def research_runs(_principal: ReadPrincipal, limit: int = 200) -> list[StrategyRun]:
    return store.list_strategy_runs(min(max(limit, 1), 2000))


@app.post("/v1/research/replay/{symbol}", response_model=ReplayResult)
async def research_replay(
    symbol: str,
    strategy: StrategyConfig,
    _principal: ReadPrincipal,
    timeframe: str = "1m",
) -> ReplayResult:
    return research.replay(symbol, strategy, timeframe=timeframe)


@app.post("/v1/research/walk-forward", response_model=WalkForwardResult)
async def research_walk_forward(
    request: WalkForwardRequest,
    _principal: ReadPrincipal,
) -> WalkForwardResult:
    try:
        return research.walk_forward(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/research/video-ea/plan", response_model=VideoEaPlan)
async def research_video_ea_plan(
    request: VideoEaPlanRequest,
    _principal: StrategyPrincipal,
) -> VideoEaPlan:
    _require_video_ea_paper_mode()
    if not request.research_only:
        raise HTTPException(status_code=422, detail="video EA plans must be research-only")
    metadata = service.instruments.get(request.symbol)
    if metadata is not None:
        request = request.model_copy(
            update={
                "config": request.config.model_copy(
                    update={
                        "tick_size": metadata.tick_size or request.config.tick_size,
                        "lower_price_band": metadata.lower_price_band,
                        "upper_price_band": metadata.upper_price_band,
                    }
                )
            }
        )
    try:
        plan = video_ea_planner.plan(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if plan.executable or not plan.research_only:
        raise HTTPException(status_code=422, detail="video EA plan failed closed")
    store.add_audit(
        "video_ea.plan_created",
        f"video EA research plan created for {plan.symbol}",
        {"symbol": plan.symbol, "trigger_count": len(plan.triggers)},
    )
    return plan


@app.post("/v1/research/video-ea/replay", response_model=VideoEaReplayResult)
async def research_video_ea_replay(
    request: VideoEaReplayRequest,
    _principal: ReadPrincipal,
) -> VideoEaReplayResult:
    _require_video_ea_paper_mode()
    result = replay_video_ea(request)
    store.add_audit(
        "video_ea.replay_completed",
        f"video EA historical replay completed for {result.symbol}",
        {
            "bars": result.bars_replayed,
            "triggers": len(result.triggered_keys),
            "duplicates": result.duplicate_crossings,
        },
    )
    return result


@app.post("/v1/research/video-ea/parameter-sweep", response_model=ParameterSweepResult)
async def research_video_ea_parameter_sweep(
    request: ParameterSweepRequest,
    _principal: StrategyPrincipal,
) -> ParameterSweepResult:
    _require_video_ea_paper_mode()
    try:
        result = parameter_sweep(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    store.add_audit(
        "video_ea.parameter_sweep_completed",
        f"video EA parameter sweep completed for {result.symbol}",
        {"combinations": result.combinations},
    )
    return result


@app.post(
    "/v1/research/video-ea/rolling-walk-forward",
    response_model=RollingWalkForwardResult,
)
async def research_video_ea_rolling_walk_forward(
    request: RollingWalkForwardRequest,
    _principal: StrategyPrincipal,
) -> RollingWalkForwardResult:
    _require_video_ea_paper_mode()
    try:
        result = rolling_walk_forward(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@app.post(
    "/v1/research/video-ea/monte-carlo",
    response_model=MonteCarloTradeStressResult,
)
async def research_video_ea_monte_carlo(
    request: MonteCarloTradeStressRequest,
    _principal: StrategyPrincipal,
) -> MonteCarloTradeStressResult:
    _require_video_ea_paper_mode()
    return monte_carlo_trade_stress(request)


@app.post(
    "/v1/research/video-ea/sensitivity",
    response_model=SensitivityResult,
)
async def research_video_ea_sensitivity(
    request: SensitivityRequest,
    _principal: StrategyPrincipal,
) -> SensitivityResult:
    _require_video_ea_paper_mode()
    try:
        return sensitivity_analysis(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/v1/research/video-ea/exposure-heatmap",
    response_model=ExposureHeatmapResult,
)
async def research_video_ea_exposure_heatmap(
    request: ExposureHeatmapRequest,
    _principal: StrategyPrincipal,
) -> ExposureHeatmapResult:
    _require_video_ea_paper_mode()
    try:
        return max_exposure_heatmap(
            request.plan,
            request.prices,
            portfolio_value=request.portfolio_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/v1/research/video-ea/lifecycle-metrics",
    response_model=BasketLifecycleMetrics,
)
async def research_video_ea_lifecycle_metrics(
    request: BasketLifecycleRequest,
    _principal: ReadPrincipal,
) -> BasketLifecycleMetrics:
    _require_video_ea_paper_mode()
    return basket_lifecycle_metrics(request)


@app.get("/v1/research/video-ea/state/{symbol}")
async def research_video_ea_state(symbol: str, _principal: ReadPrincipal):
    _require_video_ea_paper_mode()
    with video_ea_runtime_lock:
        return _load_video_ea_runtime(symbol).snapshot()


@app.post(
    "/v1/research/video-ea/arm",
    response_model=VideoEaRuntimeControlResponse,
)
async def research_video_ea_arm(
    request: VideoEaArmRequest,
    _principal: StrategyPrincipal,
) -> VideoEaRuntimeControlResponse:
    _require_video_ea_paper_mode()
    if request.plan.executable or not request.plan.research_only:
        raise HTTPException(status_code=422, detail="video EA plans must remain research-only")
    with video_ea_runtime_lock:
        runtime = _load_video_ea_runtime(request.plan.symbol)
        try:
            event = runtime.arm(request.plan, current_price=request.current_price)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        _persist_video_ea_runtime(request.plan.symbol, runtime)
    store.add_audit(
        "video_ea.cycle_armed",
        f"video EA cycle armed for {request.plan.symbol.upper()}",
        {"symbol": request.plan.symbol.upper()},
    )
    return VideoEaRuntimeControlResponse(event=event, snapshot=runtime.snapshot())


@app.post(
    "/v1/research/video-ea/price/{symbol}",
    response_model=VideoEaRuntimeControlResponse,
)
async def research_video_ea_price(
    symbol: str,
    observation: VideoEaPriceObservation,
    _principal: StrategyPrincipal,
) -> VideoEaRuntimeControlResponse:
    _require_video_ea_paper_mode()
    with video_ea_runtime_lock:
        runtime = _load_video_ea_runtime(symbol)
        event = runtime.on_price(observation.price)
        _persist_video_ea_runtime(symbol, runtime)
    return VideoEaRuntimeControlResponse(event=event, snapshot=runtime.snapshot())


@app.post(
    "/v1/research/video-ea/pause/{symbol}",
    response_model=VideoEaRuntimeControlResponse,
)
async def research_video_ea_pause(
    symbol: str,
    _principal: StrategyPrincipal,
) -> VideoEaRuntimeControlResponse:
    _require_video_ea_paper_mode()
    with video_ea_runtime_lock:
        runtime = _load_video_ea_runtime(symbol)
        event = runtime.pause()
        _persist_video_ea_runtime(symbol, runtime)
    return VideoEaRuntimeControlResponse(event=event, snapshot=runtime.snapshot())


@app.post(
    "/v1/research/video-ea/resume/{symbol}",
    response_model=VideoEaRuntimeControlResponse,
)
async def research_video_ea_resume(
    symbol: str,
    _principal: StrategyPrincipal,
) -> VideoEaRuntimeControlResponse:
    _require_video_ea_paper_mode()
    with video_ea_runtime_lock:
        runtime = _load_video_ea_runtime(symbol)
        event = runtime.resume()
        _persist_video_ea_runtime(symbol, runtime)
    return VideoEaRuntimeControlResponse(event=event, snapshot=runtime.snapshot())


@app.post(
    "/v1/research/video-ea/reset/{symbol}",
    response_model=VideoEaRuntimeControlResponse,
)
async def research_video_ea_reset(
    symbol: str,
    _principal: StrategyPrincipal,
) -> VideoEaRuntimeControlResponse:
    _require_video_ea_paper_mode()
    with video_ea_runtime_lock:
        runtime = _load_video_ea_runtime(symbol)
        event = runtime.reset()
        _persist_video_ea_runtime(symbol, runtime)
    store.add_audit(
        "video_ea.cycle_reset",
        f"video EA cycle reset for {symbol.upper()}",
        {"symbol": symbol.upper()},
    )
    return VideoEaRuntimeControlResponse(event=event, snapshot=runtime.snapshot())


@app.post("/v1/research/drift", response_model=DriftReport)
async def research_drift(request: DriftRequest, _principal: ReadPrincipal) -> DriftReport:
    return research.drift_report(
        request.expected_return_pct,
        request.observed_return_pct,
        tolerance_pct_points=request.tolerance_pct_points,
    )


@app.post("/v1/research/promotion", response_model=PromotionDecision)
async def research_promotion(
    evidence: PromotionEvidence,
    _principal: RiskPrincipal,
) -> PromotionDecision:
    return research.promotion_decision(evidence)


@app.post("/v1/production/readiness", response_model=ProductionReadinessReport)
async def production_readiness(
    evidence: ExternalReadinessEvidence,
    _principal: RiskPrincipal,
) -> ProductionReadinessReport:
    return production.report(evidence)


@app.post("/v1/production/canary-plan", response_model=CanaryPlan)
async def production_canary_plan(
    evidence: ExternalReadinessEvidence,
    _principal: RiskPrincipal,
) -> CanaryPlan:
    return production.canary_plan(evidence)


@app.get("/v1/tfex/account")
async def tfex_account(_principal: ReadPrincipal) -> dict[str, object]:
    return await _tfex_gateway().account()


@app.get("/v1/tfex/portfolio")
async def tfex_portfolio(_principal: ReadPrincipal) -> list[dict[str, object]]:
    return await _tfex_gateway().portfolio()


@app.get("/v1/tfex/orders")
async def tfex_orders(_principal: ReadPrincipal) -> list[dict[str, object]]:
    return await _tfex_gateway().orders()


@app.get("/v1/tfex/contracts", response_model=list[TfexContractMetadata])
async def tfex_contracts(_principal: ReadPrincipal) -> list[TfexContractMetadata]:
    return _tfex_gateway().contracts.list()


@app.post("/v1/tfex/risk/check", response_model=TfexRiskDecision)
async def tfex_risk_check(
    submission: TfexOrderSubmission,
    _principal: ReadPrincipal,
) -> TfexRiskDecision:
    gateway = _tfex_gateway()
    quote_age = store.quote_age_seconds(submission.intent.symbol)
    context = await gateway.risk_context(
        symbol=submission.intent.symbol,
        price=submission.intent.price,
        quote_age_seconds=quote_age,
        market_data_available=store.get_quote(submission.intent.symbol) is not None,
    )
    return tfex_risk.evaluate(TfexOrderSubmission(intent=submission.intent, risk=context))


@app.post("/v1/tfex/risk/preflight", response_model=TfexRiskDecision)
async def tfex_risk_preflight(
    intent: TfexOrderIntent,
    _principal: ReadPrincipal,
) -> TfexRiskDecision:
    gateway = _tfex_gateway()
    quote_age = store.quote_age_seconds(intent.symbol)
    context = await gateway.risk_context(
        symbol=intent.symbol,
        price=intent.price,
        quote_age_seconds=quote_age,
        market_data_available=store.get_quote(intent.symbol) is not None,
    )
    return tfex_risk.evaluate(TfexOrderSubmission(intent=intent, risk=context))


@app.post("/v1/tfex/orders/uat")
async def tfex_place_uat_order(
    submission: TfexOrderSubmission,
    principal: OrderPrincipal,
) -> dict[str, object]:
    if settings.trading_mode != "sandbox":
        raise HTTPException(status_code=409, detail="TFEX mutation is UAT-only")
    gateway = _tfex_gateway()
    context = await gateway.risk_context(
        symbol=submission.intent.symbol,
        price=submission.intent.price,
        quote_age_seconds=store.quote_age_seconds(submission.intent.symbol),
        market_data_available=store.get_quote(submission.intent.symbol) is not None,
    )
    trusted_submission = submission.model_copy(update={"risk": context})
    decision = tfex_risk.evaluate(trusted_submission)
    if not decision.approved:
        raise HTTPException(status_code=422, detail=decision.model_dump())
    try:
        result = await gateway.place_uat_order(submission.intent)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.add_audit(
        "tfex.uat_order.submitted",
        f"TFEX UAT {submission.intent.side.value} {submission.intent.symbol}",
        {"actor": principal.subject, "volume": submission.intent.volume},
    )
    return result


@app.post("/v1/tradingview/webhook")
async def tradingview_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-TV-Signature"),
) -> dict[str, object]:
    sig = (
        x_signature
        or request.headers.get("x-tradingview-signature")
        or request.headers.get("x-tv-signature")
    )
    payload_bytes = await request.body()
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="invalid json payload") from exc

    signal = tradingview_parser.parse(payload)
    if signal is None:
        raise HTTPException(status_code=422, detail="invalid tradingview alert payload")

    # Check symbol-specific secret first, fallback to global validator
    symbol_secret = tradingview_config.get_webhook_secret(signal.symbol)
    if symbol_secret:
        sym_validator = TradingViewWebhookValidator(symbol_secret)
        if not sym_validator.validate(payload_bytes, sig):
            raise HTTPException(status_code=401, detail="invalid webhook signature for symbol")
    else:
        if not tradingview_validator.validate(payload_bytes, sig):
            raise HTTPException(status_code=401, detail="invalid webhook signature")

    stored = store.add_signal(signal)
    store.add_audit(
        "tradingview.webhook",
        f"tradingview alert for {signal.symbol} {signal.action.value}",
        {"signal_id": str(stored.id), "symbol": signal.symbol},
    )
    return {"status": "accepted", "signal_id": str(stored.id)}


@app.get("/v1/tradingview/config")
async def tradingview_config_list(_principal: ReadPrincipal) -> dict[str, object]:
    items = tradingview_config.list_webhooks()
    return {
        "webhooks": [
            {"symbol": item["symbol"], "secret_configured": item["secret_configured"]}
            for item in items
        ],
    }


@app.post("/v1/tradingview/config")
async def tradingview_config_create(
    payload: dict[str, str],
    _principal: RiskPrincipal,
) -> dict[str, object]:
    symbol = payload.get("symbol")
    secret = payload.get("secret")
    if not symbol or not secret:
        raise HTTPException(status_code=422, detail="symbol and secret are required")
    tradingview_config.set_webhook_secret(symbol, secret)
    store.add_audit(
        "tradingview.config.updated",
        f"tradingview webhook config updated for {symbol}",
        {"symbol": symbol},
    )
    return {"status": "updated", "symbol": symbol}


@app.delete("/v1/tradingview/config/{symbol}")
async def tradingview_config_delete(
    symbol: str,
    _principal: RiskPrincipal,
) -> dict[str, bool]:
    deleted = tradingview_config.delete_webhook_secret(symbol)
    if deleted:
        store.add_audit(
            "tradingview.config.deleted",
            f"tradingview webhook config deleted for {symbol}",
            {"symbol": symbol},
        )
    return {"deleted": deleted}


@app.post("/v1/telegram/test")
async def telegram_test(
    message: dict[str, str],
    _principal: RiskPrincipal,
) -> dict[str, bool]:
    text = message.get("message", "zksato test notification")
    sent = await dispatch_telegram(text)
    return {"sent": sent}


# ── Agent OS Endpoints ──

agent_subaccounts = AgentSubAccountManager()
agent_engine = AgentExecutionEngine(
    settings=settings,
    trading_service=service,
    subaccount_manager=agent_subaccounts,
)


@app.get("/v1/agent-os/skills")
async def agent_os_list_skills(_principal: StrategyPrincipal) -> list[dict[str, object]]:
    return agent_engine.skills.list_skills()


@app.get("/v1/agent-os/subaccounts")
async def agent_os_list_subaccounts(_principal: StrategyPrincipal) -> list[dict[str, object]]:
    return [
        {
            "sub_account_id": a.sub_account_id,
            "agent_name": a.agent_name,
            "allocated_collateral_usd": a.allocated_collateral_usd,
            "current_cash_usd": a.current_cash_usd,
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat(),
        }
        for a in agent_subaccounts.list_subaccounts()
    ]


@app.post("/v1/agent-os/subaccounts")
async def agent_os_create_subaccount(
    payload: dict[str, object],
    _principal: RiskPrincipal,
) -> dict[str, object]:
    agent_name = str(payload.get("agent_name", "agent"))
    raw_collateral = payload.get("collateral_usd", 1000.0)
    if isinstance(raw_collateral, bool) or not isinstance(raw_collateral, (str, int, float)):
        raise HTTPException(status_code=422, detail="collateral_usd must be numeric")
    try:
        collateral = float(raw_collateral)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="collateral_usd must be numeric") from exc
    account = agent_subaccounts.create_subaccount(agent_name=agent_name, collateral_usd=collateral)
    store.add_audit(
        "agent_os.subaccount.created",
        f"created agent subaccount {account.sub_account_id} for {agent_name}",
        {"sub_account_id": account.sub_account_id, "collateral_usd": collateral},
    )
    return {
        "sub_account_id": account.sub_account_id,
        "agent_name": account.agent_name,
        "allocated_collateral_usd": account.allocated_collateral_usd,
        "current_cash_usd": account.current_cash_usd,
    }


@app.post("/v1/agent-os/execute")
async def agent_os_execute_skill(
    payload: dict[str, object],
    _principal: StrategyPrincipal,
) -> dict[str, object]:
    skill_name = str(payload.get("skill", ""))
    params = payload.get("parameters", {})
    if not isinstance(params, dict) or not skill_name:
        raise HTTPException(status_code=422, detail="skill and parameters dict required")
    result = await agent_engine.skills.execute_skill(skill_name, **params)
    return result


@app.post("/v1/telegram/webhook")
async def telegram_webhook(payload: dict[str, Any]) -> dict[str, bool]:
    notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    if not notifier.enabled:
        return {"ok": True}

    msg = payload.get("message")
    if not isinstance(msg, dict):
        return {"ok": True}

    text = str(msg.get("text", "")).strip()
    chat = msg.get("chat", {})
    chat_id = chat.get("id", settings.telegram_chat_id)

    if text.startswith("/"):
        portfolio_summary: dict[str, Any] | None = None
        command_name = text.split("@", 1)[0].strip().lower()
        if command_name == "/pnl":
            snapshot = await service.portfolio(record_snapshot=False)
            portfolio_summary = {
                "total": snapshot.realized_pnl + snapshot.unrealized_pnl,
                "currency": "USDT",
            }
        resp = await notifier.handle_telegram_command(
            text,
            chat_id,
            system_status={
                "environment": settings.environment,
                "execution_mode": settings.trading_mode,
                "kill_switch_active": settings.kill_switch,
            },
            portfolio_summary=portfolio_summary,
            quotes=[{"symbol": q.symbol, "price": q.last} for q in store.list_quotes()],
        )
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                url,
                json={"chat_id": chat_id, "text": resp, "parse_mode": "Markdown"},
            )

    return {"ok": True}
