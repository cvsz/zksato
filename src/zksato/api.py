from __future__ import annotations

from fastapi import FastAPI, HTTPException

from zksato.broker.paper import PaperBroker
from zksato.config import get_settings
from zksato.domain import OrderRecord, OrderSubmission, RiskDecision
from zksato.service import RiskRejectedError, TradingModeError, TradingService

settings = get_settings()
service = TradingService(settings=settings, broker=PaperBroker())

app = FastAPI(
    title="zksato",
    version="0.1.0",
    description="Risk-first automated trading control plane",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": settings.trading_mode}


@app.get("/v1/config")
async def config() -> dict[str, object]:
    # Intentionally expose only non-secret operational policy.
    return {
        "environment": settings.environment,
        "trading_mode": settings.trading_mode,
        "live_trading_enabled": settings.live_trading_enabled,
        "risk": {
            "max_positions": settings.max_positions,
            "max_position_pct": settings.max_position_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_drawdown_pct": settings.max_drawdown_pct,
            "require_stop_loss": settings.require_stop_loss,
        },
    }


@app.post("/v1/risk/check", response_model=RiskDecision)
async def risk_check(submission: OrderSubmission) -> RiskDecision:
    return service.check_risk(submission)


@app.post("/v1/orders", response_model=OrderRecord, status_code=201)
async def place_order(submission: OrderSubmission) -> OrderRecord:
    try:
        return await service.submit(submission)
    except RiskRejectedError as exc:
        raise HTTPException(status_code=422, detail=exc.decision.model_dump()) from exc
    except TradingModeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/orders", response_model=list[OrderRecord])
async def list_orders() -> list[OrderRecord]:
    return await service.list_orders()
