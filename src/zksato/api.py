from __future__ import annotations

from contextlib import asynccontextmanager
from time import monotonic
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from zksato.approvals import ApprovalRepository, ApprovalRequest, LiveApproval
from zksato.auth import AuthManager, Principal, Role, require_roles
from zksato.automation import AutomationEngine
from zksato.backtest import Backtester
from zksato.broker.paper import PaperBroker
from zksato.broker.settrade import SettradeBroker
from zksato.config import get_settings
from zksato.dashboard import DASHBOARD_HTML
from zksato.domain import (
    AlertRule,
    BacktestRequest,
    BacktestResult,
    BotConfig,
    BotStatus,
    DashboardSnapshot,
    OrderIntent,
    OrderRecord,
    OrderSubmission,
    PortfolioSnapshot,
    Quote,
    ReconciliationReport,
    RiskDecision,
    ScannerResult,
    Signal,
)
from zksato.market import DemoMarketFeed
from zksato.market_settrade import SettradeRealtimeFeed
from zksato.notifications import OutboxDispatcher
from zksato.observability import HTTP_LATENCY, HTTP_REQUESTS, metrics_response
from zksato.persistence import build_store
from zksato.reconcile import ReconciliationService, ReconciliationWorker
from zksato.scanner import MarketScanner
from zksato.security import RateLimitMiddleware, SecurityHeadersMiddleware
from zksato.service import RiskRejectedError, TradingModeError, TradingService
from zksato.tfex import (
    SettradeTfexGateway,
    TfexOrderIntent,
    TfexOrderSubmission,
    TfexRiskDecision,
    TfexRiskEngine,
)

settings = get_settings()
store = build_store(settings)
approvals = ApprovalRepository(settings.database_url)
if settings.trading_mode == "paper":
    broker = PaperBroker(store=store, initial_cash=settings.initial_cash)
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
backtester = Backtester()
scanner = MarketScanner()
auth = AuthManager(settings)
reconciler = ReconciliationService(broker=broker, store=store)
reconciliation_worker = ReconciliationWorker(
    service=reconciler,
    interval_seconds=settings.reconciliation_interval_seconds,
)
outbox_dispatcher = OutboxDispatcher(
    store=store,
    webhook_url=settings.notification_webhook_url,
)
settrade_feed: SettradeRealtimeFeed | None = None
tfex_gateway: SettradeTfexGateway | None = None
tfex_risk = TfexRiskEngine(settings)

read_access = require_roles(auth, Role.READ_ONLY)
strategy_access = require_roles(auth, Role.STRATEGY_OPERATOR)
order_access = require_roles(auth, Role.ORDER_APPROVER)
risk_access = require_roles(auth, Role.RISK_ADMIN)
ReadPrincipal = Annotated[Principal, Depends(read_access)]
StrategyPrincipal = Annotated[Principal, Depends(strategy_access)]
OrderPrincipal = Annotated[Principal, Depends(order_access)]
RiskPrincipal = Annotated[Principal, Depends(risk_access)]
LiveApprovalHeader = Annotated[str | None, Header(alias="X-Live-Approval-Id")]


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.trading_mode != "paper" and settings.reconciliation_enabled:
        reconciliation_worker.start()
    outbox_dispatcher.start()
    yield
    await reconciliation_worker.stop()
    await outbox_dispatcher.stop()
    if settrade_feed is not None:
        settrade_feed.stop()
    approvals.close()
    store.close()


app = FastAPI(
    title="zksato",
    version="0.3.0",
    description="Risk-first automated trading control plane with dashboard",
    lifespan=lifespan,
)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
)
app.add_middleware(SecurityHeadersMiddleware)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Live-Approval-Id"],
        allow_credentials=False,
    )
if settings.trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)


@app.middleware("http")
async def observe_http(request: Request, call_next):
    started = monotonic()
    response = await call_next(request)
    route = request.scope.get("route")
    route_name = getattr(route, "path", request.url.path)
    HTTP_REQUESTS.labels(
        method=request.method,
        route=route_name,
        status=str(response.status_code),
    ).inc()
    HTTP_LATENCY.labels(method=request.method, route=route_name).observe(monotonic() - started)
    return response


def _tfex_gateway() -> SettradeTfexGateway:
    global tfex_gateway
    if settings.trading_mode == "paper":
        raise HTTPException(status_code=409, detail="TFEX gateway requires sandbox/live mode")
    if not settings.settrade_tfex_configured:
        raise HTTPException(status_code=409, detail="Settrade TFEX credentials are incomplete")
    if tfex_gateway is None:
        try:
            tfex_gateway = SettradeTfexGateway(settings)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return tfex_gateway


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page() -> str:
    if not settings.dashboard_enabled:
        raise HTTPException(status_code=404, detail="dashboard disabled")
    return DASHBOARD_HTML


@app.get("/health")
async def health() -> dict[str, object]:
    database_healthy = store.health()
    return {
        "status": "ok" if database_healthy else "degraded",
        "mode": settings.trading_mode,
        "automation": automation.status.state,
        "settrade_configured": settings.settrade_configured,
        "settrade_tfex_configured": settings.settrade_tfex_configured,
        "persistence": "sql" if settings.database_url else "memory",
        "persistence_healthy": database_healthy,
    }


@app.get("/metrics", include_in_schema=False)
async def metrics(_principal: ReadPrincipal):
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="metrics disabled")
    return metrics_response()


@app.get("/v1/auth/me")
async def auth_me(principal: ReadPrincipal) -> dict[str, str]:
    return {"subject": principal.subject, "role": principal.role.value}


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
        "settrade_configured": settings.settrade_configured,
        "settrade_tfex_configured": settings.settrade_tfex_configured,
        "watchlist": settings.watchlist,
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
            "max_symbol_exposure_pct": settings.max_symbol_exposure_pct,
            "market_data_stale_seconds": settings.market_data_stale_seconds,
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
    if settrade_feed is None:
        settrade_feed = SettradeRealtimeFeed(settings, automation)
    try:
        settrade_feed.start(settings.watchlist)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.add_audit("market.settrade.started", "Settrade realtime subscriptions started")
    return {"running": True, "symbols": settings.watchlist}


@app.post("/v1/market/settrade/stop")
async def stop_settrade_feed(_principal: StrategyPrincipal) -> dict[str, bool]:
    if settrade_feed is not None:
        settrade_feed.stop()
    store.add_audit("market.settrade.stopped", "Settrade realtime subscriptions stopped")
    return {"running": False}


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
    return service.check_risk(submission)


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
async def list_orders(_principal: ReadPrincipal) -> list[OrderRecord]:
    return await service.list_orders()


@app.delete("/v1/orders/{order_id}", response_model=OrderRecord)
async def cancel_order(order_id: str, _principal: OrderPrincipal) -> OrderRecord:
    try:
        return await service.cancel_order(order_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/v1/reconcile", response_model=ReconciliationReport)
async def reconcile_orders(_principal: OrderPrincipal) -> ReconciliationReport:
    try:
        return await reconciler.run()
    except (RuntimeError, OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/portfolio", response_model=PortfolioSnapshot)
async def portfolio(_principal: ReadPrincipal) -> PortfolioSnapshot:
    return await service.portfolio()


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
async def audit(_principal: ReadPrincipal, limit: int = 100) -> list[dict[str, object]]:
    return [event.model_dump(mode="json") for event in store.list_audit(min(max(limit, 1), 1000))]


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


@app.get("/v1/tfex/account")
async def tfex_account(_principal: ReadPrincipal) -> dict[str, object]:
    return await _tfex_gateway().account()


@app.get("/v1/tfex/portfolio")
async def tfex_portfolio(_principal: ReadPrincipal) -> list[dict[str, object]]:
    return await _tfex_gateway().portfolio()


@app.get("/v1/tfex/orders")
async def tfex_orders(_principal: ReadPrincipal) -> list[dict[str, object]]:
    return await _tfex_gateway().orders()


@app.post("/v1/tfex/risk/check", response_model=TfexRiskDecision)
async def tfex_risk_check(
    submission: TfexOrderSubmission,
    _principal: ReadPrincipal,
) -> TfexRiskDecision:
    return tfex_risk.evaluate(submission)


@app.post("/v1/tfex/risk/preflight", response_model=TfexRiskDecision)
async def tfex_risk_preflight(
    intent: TfexOrderIntent,
    _principal: ReadPrincipal,
) -> TfexRiskDecision:
    gateway = _tfex_gateway()
    quote_age = store.quote_age_seconds(intent.symbol)
    context = await gateway.risk_context(
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
