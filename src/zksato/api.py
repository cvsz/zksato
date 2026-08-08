from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

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
    OrderRecord,
    OrderSubmission,
    PortfolioSnapshot,
    Quote,
    RiskDecision,
    Signal,
)
from zksato.market import DemoMarketFeed
from zksato.service import RiskRejectedError, TradingModeError, TradingService
from zksato.store import StateStore

settings = get_settings()
store = StateStore()
if settings.trading_mode == "paper":
    broker = PaperBroker(store=store, initial_cash=settings.initial_cash)
else:
    broker = SettradeBroker(settings=settings)
service = TradingService(settings=settings, broker=broker, store=store)
automation = AutomationEngine(settings=settings, store=store, service=service)
demo_feed = DemoMarketFeed(automation=automation)
backtester = Backtester()

app = FastAPI(
    title="zksato",
    version="0.2.0",
    description="Risk-first automated trading control plane with dashboard",
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page() -> str:
    if not settings.dashboard_enabled:
        raise HTTPException(status_code=404, detail="dashboard disabled")
    return DASHBOARD_HTML


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "mode": settings.trading_mode,
        "automation": automation.status.state,
        "settrade_configured": settings.settrade_configured,
    }


@app.get("/v1/config")
async def config() -> dict[str, object]:
    return {
        "environment": settings.environment,
        "trading_mode": settings.trading_mode,
        "live_trading_enabled": settings.live_trading_enabled,
        "live_requires_confirmation": settings.live_requires_confirmation,
        "automation_enabled": settings.automation_enabled,
        "settrade_configured": settings.settrade_configured,
        "watchlist": settings.watchlist,
        "risk": {
            "kill_switch": settings.kill_switch,
            "max_positions": settings.max_positions,
            "max_position_pct": settings.max_position_pct,
            "max_risk_per_trade_pct": settings.max_risk_per_trade_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_drawdown_pct": settings.max_drawdown_pct,
            "max_orders_per_day": settings.max_orders_per_day,
            "max_notional_per_order": settings.max_notional_per_order,
            "require_stop_loss": settings.require_stop_loss,
        },
    }


@app.get("/v1/dashboard", response_model=DashboardSnapshot)
async def dashboard_snapshot() -> DashboardSnapshot:
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
async def ingest_quote(quote: Quote) -> Quote:
    await automation.on_quote(quote)
    return quote


@app.get("/v1/market/quotes", response_model=list[Quote])
async def list_quotes() -> list[Quote]:
    return store.list_quotes()


@app.get("/v1/market/history/{symbol}")
async def price_history(symbol: str) -> dict[str, object]:
    return {"symbol": symbol.upper(), "prices": store.get_prices(symbol)}


@app.post("/v1/market/demo/start")
async def start_demo() -> dict[str, object]:
    if settings.trading_mode != "paper":
        raise HTTPException(status_code=409, detail="demo feed is only available in paper mode")
    demo_feed.start(settings.watchlist)
    store.add_audit("market.demo.started", "synthetic paper feed started")
    return {"running": True, "symbols": settings.watchlist}


@app.post("/v1/market/demo/stop")
async def stop_demo() -> dict[str, bool]:
    await demo_feed.stop()
    store.add_audit("market.demo.stopped", "synthetic paper feed stopped")
    return {"running": False}


@app.post("/v1/bot/start", response_model=BotStatus)
async def start_bot(bot_config: BotConfig) -> BotStatus:
    if not settings.automation_enabled:
        raise HTTPException(status_code=409, detail="automation is disabled by server policy")
    if settings.trading_mode == "live" and bot_config.auto_execute:
        raise HTTPException(
            status_code=409,
            detail="autonomous live execution is disabled; use signal-only mode",
        )
    return automation.start(bot_config)


@app.post("/v1/bot/stop", response_model=BotStatus)
async def stop_bot() -> BotStatus:
    return automation.stop()


@app.post("/v1/bot/tick", response_model=BotStatus)
async def bot_tick() -> BotStatus:
    return await automation.tick()


@app.get("/v1/bot", response_model=BotStatus)
async def bot_status() -> BotStatus:
    return automation.status


@app.post("/v1/risk/check", response_model=RiskDecision)
async def risk_check(submission: OrderSubmission) -> RiskDecision:
    return service.check_risk(submission)


@app.post("/v1/orders", response_model=OrderRecord, status_code=201)
async def place_order(submission: OrderSubmission) -> OrderRecord:
    try:
        return await service.submit(submission, automated=False)
    except RiskRejectedError as exc:
        raise HTTPException(status_code=422, detail=exc.decision.model_dump()) from exc
    except TradingModeError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/orders", response_model=list[OrderRecord])
async def list_orders() -> list[OrderRecord]:
    return await service.list_orders()


@app.delete("/v1/orders/{order_id}", response_model=OrderRecord)
async def cancel_order(order_id: str) -> OrderRecord:
    try:
        return await service.cancel_order(order_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/portfolio", response_model=PortfolioSnapshot)
async def portfolio() -> PortfolioSnapshot:
    return await service.portfolio()


@app.get("/v1/signals", response_model=list[Signal])
async def signals(limit: int = 100) -> list[Signal]:
    return store.list_signals(min(max(limit, 1), 1000))


@app.post("/v1/alerts", response_model=AlertRule, status_code=201)
async def create_alert(alert: AlertRule) -> AlertRule:
    store.add_audit("alert.created", f"alert created for {alert.symbol}")
    return store.add_alert(alert)


@app.get("/v1/alerts", response_model=list[AlertRule])
async def list_alerts() -> list[AlertRule]:
    return store.list_alerts()


@app.delete("/v1/alerts/{alert_id}")
async def delete_alert(alert_id: str) -> dict[str, bool]:
    return {"deleted": store.delete_alert(alert_id)}


@app.get("/v1/audit")
async def audit(limit: int = 100) -> list[dict[str, object]]:
    return [event.model_dump(mode="json") for event in store.list_audit(min(max(limit, 1), 1000))]


@app.post("/v1/backtest", response_model=BacktestResult)
async def backtest(request: BacktestRequest) -> BacktestResult:
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
