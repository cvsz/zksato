"""
Freqtrade-compatible API routes for zksato.

These endpoints provide strategy management, enhanced backtesting,
hyperopt optimization, protections, pairlist management, and LLM
client configuration. All features are advisory/research only —
order execution always routes through RiskEngine and TradingService.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

# Agent trading service and session management
from zksato.agent_trading.service import AgentService
from zksato.auth import AuthManager, Principal, Role
from zksato.backtest_enhanced import EnhancedBacktester
from zksato.config import get_settings
from zksato.domain import Candle, Side
from zksato.hyperopt import LOSS_FUNCTIONS, run_hyperopt
from zksato.llm_clients import (
    DEFAULT_CATALOG,
    create_llm_client,
    detect_api_key_env,
    get_api_key,
    get_capabilities,
    mask_api_key,
    require_api_key,
    validate_model,
)
from zksato.pairlist import (
    ChangePctPairList,
    MomentumPairList,
    PairInfo,
    PairList,
    PairListManager,
    SectorDiversifiedPairList,
    StaticPairList,
    VolatilityPairList,
    VolumePairList,
)
from zksato.protections import (
    ConsecutiveLossProtection,
    CooldownPeriodProtection,
    DrawdownProtection,
    Protection,
    ProtectionManager,
    StoplossGuardProtection,
    TimeBasedProtection,
    TradeContext,
    VolatilityProtection,
)
from zksato.security import AgentRateLimiter
from zksato.store import StateStore
from zksato.strategy_freqtrade import IStrategy, strategy_registry
from zksato.trailing_stop import TrailingStopManager

# Local auth manager (uses cached settings, same as api.py)
_local_settings = get_settings()


def _platform_principal(
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    session_token: Annotated[str | None, Cookie(alias=_local_settings.session_cookie_name)] = None,
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> Principal:
    """Auth dependency for freqtrade routes (mirrors api.py pattern)."""
    if not _local_settings.auth_required:
        return Principal(
            subject="local-dev",
            role=Role.PLATFORM_ADMIN,
            auth_method="local",
        )
    _local_auth = AuthManager(_local_settings)
    principal = _local_auth.authenticate(
        authorization,
        x_api_key,
        session_token=session_token,
        csrf_token=x_csrf_token,
        method="GET",
    )
    return _local_auth.require(principal, {Role.PLATFORM_ADMIN})


PlatformPrincipal = Annotated[Principal, Depends(_platform_principal)]

router = APIRouter(prefix="/v1/freqtrade", tags=["freqtrade"])

# ── Module-level state (in-memory, reset on restart) ───────────────────────

_pairlist_manager = PairListManager()
_protection_manager = ProtectionManager()
_trailing_stop_manager: TrailingStopManager | None = None
_strategy_instances: dict[str, IStrategy] = {}
_hyperopt_results: dict[str, Any] = {}
_agent_rate_limiter = AgentRateLimiter()
_agent_sessions: dict[str, dict[str, Any]] = {}


# ── Request/Response Models ───────────────────────────────────────────────


class StrategyRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    class_path: str = Field(..., description="Python import path to strategy class")


class StrategyParameterSet(BaseModel):
    parameter: str
    value: Any


class StrategyListResponse(BaseModel):
    strategies: list[str]
    details: dict[str, dict[str, Any]]


class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    strategy: str = Field(..., min_length=1)
    candles: list[dict[str, Any]] = Field(default_factory=list)
    initial_cash: float = Field(default=100_000.0, gt=0)
    commission_pct: float = Field(default=0.15, ge=0, le=5)
    slippage_pct: float = Field(default=0.05, ge=0, le=5)


class HyperoptRequest(BaseModel):
    strategy: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1, max_length=32)
    candles: list[dict[str, Any]] = Field(default_factory=list)
    loss_function: str = Field(default="OnlyProfitHyperOptLoss")
    n_epochs: int = Field(default=100, ge=1, le=10000)
    timeout: float | None = Field(default=None, ge=0)
    seed: int | None = None
    spaces: list[str] | None = None


class LossFunctionInfo(BaseModel):
    name: str
    direction: str


class ProtectionConfigureRequest(BaseModel):
    # "cooldown", "stoploss_guard", "drawdown", "volatility", "time_based", "consecutive_loss"
    protection: str
    params: dict[str, Any] = Field(default_factory=dict)


class PairListConfigureRequest(BaseModel):
    # "static", "volume", "change_pct", "momentum", "volatility", "sector_diversified"
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class TrailingStopConfigureRequest(BaseModel):
    enabled: bool = False
    trailing_stop_positive: float | None = None
    trailing_stop_positive_offset: float | None = None
    trailing_only_offset_is_reached: bool = False


class LLMClientCreateRequest(BaseModel):
    provider: str
    model: str
    base_url: str | None = None


class SessionCreateRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=64)
    ttl_seconds: int = Field(default=3600, ge=60, le=86400)


class SessionResponse(BaseModel):
    session_token: str
    agent_id: str
    expires_at: str
    ttl_seconds: int


class SessionValidateResponse(BaseModel):
    valid: bool
    agent_id: str | None = None
    expires_at: str | None = None


# ── Strategy Endpoints ───────────────────────────────────────────────────


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies(_principal: PlatformPrincipal) -> StrategyListResponse:
    """List all registered trading strategies."""
    names = strategy_registry.list()
    details = {}
    for name in names:
        strategy_class = strategy_registry.get(name)
        if strategy_class:
            instance = strategy_class()
            details[name] = {
                "description": instance.description,
                "timeframe": instance.timeframe,
                "stoploss": instance.stoploss,
                "max_open_trades": instance.max_open_trades,
                "hyperopt_params": {
                    pname: {
                        "type": type(p).__name__,
                        "space": p.space,
                        "default": p.default,
                        "value": p.value,
                        "optimize": p.optimize,
                    }
                    for pname, p in instance.hyperopt_params.items()
                },
                "roi_table": [{"period": r.period, "profit": r.profit} for r in instance.roi_table],
                "protections": [
                    {"method": p.method, "params": p.params} for p in (instance.protections or [])
                ],
            }
    return StrategyListResponse(strategies=names, details=details)


@router.post("/strategies/register")
async def register_strategy(
    request: StrategyRegisterRequest,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Register a strategy class by import path."""
    try:
        module_path, class_name = request.class_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        strategy_class = getattr(module, class_name)
        strategy_registry.register(strategy_class)
        return {"status": "registered", "name": request.name}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/strategies/{name}/parameters")
async def get_strategy_parameters(
    name: str,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Get hyperoptable parameters for a strategy."""
    strategy_class = strategy_registry.get(name)
    if strategy_class is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    instance = strategy_class()
    return {
        "name": name,
        "parameters": {
            pname: {
                "type": type(p).__name__,
                "space": p.space,
                "default": p.default,
                "value": p.value,
                "optimize": p.optimize,
                "load": p.load,
            }
            for pname, p in instance.hyperopt_params.items()
        },
    }


@router.post("/strategies/{name}/parameters")
async def set_strategy_parameter(
    name: str,
    request: StrategyParameterSet,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Set a hyperoptable parameter value for a strategy."""
    strategy_class = strategy_registry.get(name)
    if strategy_class is None:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    if name not in _strategy_instances:
        _strategy_instances[name] = strategy_class()
    instance = _strategy_instances[name]
    try:
        instance.set_hyperopt_param(request.parameter, request.value)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "updated",
        "name": name,
        "parameter": request.parameter,
        "value": request.value,
    }


# ── Backtesting Endpoints ────────────────────────────────────────────────


@router.post("/backtest")
async def run_backtest(
    request: BacktestRequest,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Run an enhanced backtest with Freqtrade-style metrics."""
    backtester = EnhancedBacktester(
        initial_cash=request.initial_cash,
        commission_pct=request.commission_pct,
        slippage_pct=request.slippage_pct,
    )

    # Convert candle dicts to Candle objects
    candles = []
    for c in request.candles:
        try:
            candles.append(
                Candle(
                    timestamp=c["timestamp"],
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c.get("volume", 0.0),
                )
            )
        except (KeyError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid candle data: {exc}") from exc

    result = backtester.run(
        symbol=request.symbol,
        candles=candles,
        signals=None,
        strategy_name=request.strategy,
    )

    return {
        "symbol": result["symbol"],
        "strategy_name": result["strategy_name"],
        "metrics": {
            "total_trades": result["metrics"].total_trades,
            "total_profit_pct": result["metrics"].total_profit_pct,
            "absolute_profit": result["metrics"].absolute_profit,
            "final_balance": result["metrics"].final_balance,
            "starting_balance": result["metrics"].starting_balance,
            "sharpe_closed": result["metrics"].sharpe_closed,
            "sortino_closed": result["metrics"].sortino_closed,
            "calmar_closed": result["metrics"].calmar_closed,
            "sqn": result["metrics"].sqn,
            "profit_factor": result["metrics"].profit_factor,
            "expectancy_ratio": result["metrics"].expectancy_ratio,
            "max_consecutive_wins": result["metrics"].max_consecutive_wins,
            "max_consecutive_losses": result["metrics"].max_consecutive_losses,
            "absolute_drawdown_pct": result["metrics"].absolute_drawdown_pct,
            "win_rate": (result["metrics"].days_win / max(result["metrics"].total_trades, 1) * 100),
        },
        "pair_performance": [
            {
                "pair": p.pair,
                "trades": p.trades,
                "avg_profit_pct": p.avg_profit_pct,
                "total_profit_pct": p.total_profit_pct,
                "wins": p.wins,
                "losses": p.losses,
                "win_rate": p.win_rate,
            }
            for p in result["pair_performance"]
        ],
        "exit_reasons": [
            {
                "exit_reason": e.exit_reason,
                "exits": e.exits,
                "avg_profit_pct": e.avg_profit_pct,
                "total_profit_pct": e.total_profit_pct,
                "win_rate": e.win_rate,
            }
            for e in result["exit_reasons"]
        ],
    }


# ── Hyperopt Endpoints ───────────────────────────────────────────────────


@router.get("/hyperopt/loss-functions", response_model=list[LossFunctionInfo])
async def list_loss_functions(_principal: PlatformPrincipal) -> list[LossFunctionInfo]:
    """List available hyperopt loss functions."""
    return [
        LossFunctionInfo(name=name, direction=cls.direction.value)
        for name, cls in LOSS_FUNCTIONS.items()
    ]


@router.post("/hyperopt/run")
async def run_hyperopt_endpoint(
    request: HyperoptRequest,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Run hyperopt parameter optimization."""
    try:
        result = run_hyperopt(
            strategy_name=request.strategy,
            symbol=request.symbol,
            candles=request.candles,
            loss_function=request.loss_function,
            n_epochs=request.n_epochs,
            timeout=request.timeout,
            seed=request.seed,
            spaces=request.spaces,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Store result for later retrieval
    result_key = f"{request.strategy}:{request.symbol}"
    _hyperopt_results[result_key] = result

    best = result.best_trial
    return {
        "strategy_name": result.strategy_name,
        "symbol": result.symbol,
        "loss_function": result.loss_function,
        "n_epochs": result.n_epochs,
        "best_loss": best.loss if best else None,
        "best_params": best.params if best else {},
        "best_metrics": best.metrics if best else {},
        "n_trials": len(result.all_trials),
    }


# ── Protections Endpoints ────────────────────────────────────────────────


@router.get("/protections")
async def list_protections(_principal: PlatformPrincipal) -> dict[str, Any]:
    """List configured protections."""
    return {
        "protections": [
            {
                "name": p.name,
                "type": type(p).__name__,
            }
            for p in _protection_manager.protections
        ]
    }


@router.post("/protections/configure")
async def configure_protection(
    request: ProtectionConfigureRequest,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Configure a protection mechanism."""
    try:
        protection: Protection
        if request.protection == "cooldown":
            protection = CooldownPeriodProtection(
                stop_duration_candles=int(request.params.get("stop_duration_candles", 4)),
                candle_duration_seconds=int(request.params.get("candle_duration_seconds", 60)),
            )
        elif request.protection == "stoploss_guard":
            protection = StoplossGuardProtection(
                lookback_period_candles=int(request.params.get("lookback_period_candles", 72)),
                trade_limit=int(request.params.get("trade_limit", 4)),
                stop_duration_candles=int(request.params.get("stop_duration_candles", 4)),
                only_per_pair=bool(request.params.get("only_per_pair", False)),
                candle_duration_seconds=int(request.params.get("candle_duration_seconds", 3600)),
            )
        elif request.protection == "drawdown":
            protection = DrawdownProtection(
                max_daily_drawdown_pct=float(request.params.get("max_daily_drawdown_pct", 5.0)),
            )
        elif request.protection == "volatility":
            protection = VolatilityProtection(
                max_volatility_pct=float(request.params.get("max_volatility_pct", 5.0)),
                lookback_trades=int(request.params.get("lookback_trades", 20)),
            )
        elif request.protection == "time_based":
            protection = TimeBasedProtection(
                blocked_hours=request.params.get("blocked_hours", [12, 13]),
                timezone_name=str(request.params.get("timezone_name", "Asia/Bangkok")),
            )
        elif request.protection == "consecutive_loss":
            protection = ConsecutiveLossProtection(
                max_consecutive_losses=int(request.params.get("max_consecutive_losses", 3)),
                stop_duration_candles=int(request.params.get("stop_duration_candles", 6)),
                candle_duration_seconds=int(request.params.get("candle_duration_seconds", 3600)),
            )
        else:
            raise ValueError(f"Unknown protection type: {request.protection}")

        _protection_manager.add(protection)
        return {"status": "added", "protection": protection.name}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/protections/evaluate")
async def evaluate_protections(
    symbol: str = Query(..., min_length=1, max_length=32),
    side: str = Query(default="buy", pattern="^(buy|sell)$"),
    amount: float = Query(default=1.0, gt=0),
    price: float | None = Query(default=None),
    current_time: str | None = Query(default=None),
    _principal: PlatformPrincipal | None = None,
) -> dict[str, Any]:
    """Evaluate all protections for a potential trade."""
    from datetime import UTC, datetime

    ct = datetime.now(UTC)
    if current_time:
        ct = datetime.fromisoformat(current_time)

    context = TradeContext(
        symbol=symbol,
        side=Side.BUY if side == "buy" else Side.SELL,
        order_type=None,
        amount=amount,
        price=price,
        current_time=ct,
    )

    result = _protection_manager.evaluate_all(context)
    return {
        "allowed": result.allowed,
        "reason": result.reason,
    }


# ── Pairlist Endpoints ───────────────────────────────────────────────────


@router.get("/pairlist")
async def get_pairlist(_principal: PlatformPrincipal) -> dict[str, Any]:
    """Get current pairlist configuration."""
    return {
        "type": type(_pairlist_manager.pairlist).__name__ if _pairlist_manager.pairlist else None,
    }


@router.post("/pairlist/configure")
async def configure_pairlist(
    request: PairListConfigureRequest,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Configure the pairlist provider."""
    try:
        pairlist: PairList
        if request.type == "static":
            pairlist = StaticPairList(
                whitelist=request.params.get("whitelist"),
                blacklist=request.params.get("blacklist"),
            )
        elif request.type == "volume":
            pairlist = VolumePairList(
                number_assets=int(request.params.get("number_assets", 50)),
                min_volume=float(request.params.get("min_volume", 0.0)),
            )
        elif request.type == "change_pct":
            pairlist = ChangePctPairList(
                number_assets=int(request.params.get("number_assets", 50)),
                min_change_pct=float(request.params.get("min_change_pct", 0.0)),
                max_change_pct=request.params.get("max_change_pct"),
            )
        elif request.type == "momentum":
            pairlist = MomentumPairList(
                number_assets=int(request.params.get("number_assets", 50)),
                min_change_pct=float(request.params.get("min_change_pct", 0.0)),
                top_only=bool(request.params.get("top_only", True)),
            )
        elif request.type == "volatility":
            pairlist = VolatilityPairList(
                max_volatility_pct=float(request.params.get("max_volatility_pct", 5.0)),
                number_assets=int(request.params.get("number_assets", 50)),
            )
        elif request.type == "sector_diversified":
            pairlist = SectorDiversifiedPairList(
                max_per_sector=int(request.params.get("max_per_sector", 5)),
                number_assets=int(request.params.get("number_assets", 50)),
            )
        else:
            raise ValueError(f"Unknown pairlist type: {request.type}")

        _pairlist_manager.set_pairlist(pairlist)
        return {"status": "configured", "type": pairlist.name}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pairlist/filter")
async def filter_pairs(
    pairs: list[PairInfo],
    _principal: PlatformPrincipal,
) -> list[PairInfo]:
    """Filter a list of pairs through the configured pairlist."""
    return _pairlist_manager.filter_pairs(pairs)


@router.get("/pairlist/is-tradeable/{symbol}")
async def is_tradeable(
    symbol: str,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Check if a symbol is tradeable."""
    # Need pairs list context — return configuration-based answer
    return {
        "symbol": symbol,
        "tradeable": True,  # Cannot determine without pairs context
        "pairlist": type(_pairlist_manager.pairlist).__name__
        if _pairlist_manager.pairlist
        else None,
    }


# ── Trailing Stop Endpoints ──────────────────────────────────────────────


@router.get("/trailing-stop")
async def get_trailing_stop(_principal: PlatformPrincipal) -> dict[str, Any]:
    """Get trailing stop configuration and state."""
    if _trailing_stop_manager is None:
        return {"configured": False}
    return {
        "configured": True,
        "trailing_stop_positive": _trailing_stop_manager.trailing_stop_positive,
        "trailing_stop_positive_offset": _trailing_stop_manager.trailing_stop_positive_offset,
        "trailing_only_offset_is_reached": _trailing_stop_manager.trailing_only_offset_is_reached,
        "states": {
            symbol: {
                "side": state.side.value,
                "entry_price": state.entry_price,
                "current_stop_price": state.current_stop_price,
                "highest_price": state.highest_price,
                "lowest_price": state.lowest_price,
                "trailing_activated": state.trailing_activated,
            }
            for symbol, state in _trailing_stop_manager.get_all_states().items()
        },
    }


@router.post("/trailing-stop/configure")
async def configure_trailing_stop(
    request: TrailingStopConfigureRequest,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Configure trailing stop parameters."""
    global _trailing_stop_manager
    _trailing_stop_manager = TrailingStopManager(
        trailing_stop_positive=request.trailing_stop_positive,
        trailing_stop_positive_offset=request.trailing_stop_positive_offset,
        trailing_only_offset_is_reached=request.trailing_only_offset_is_reached,
    )
    return {
        "status": "configured",
        "enabled": request.enabled,
    }


# ── LLM Client Endpoints ─────────────────────────────────────────────────


@router.get("/llm/providers")
async def list_llm_providers(_principal: PlatformPrincipal) -> dict[str, Any]:
    """List available LLM providers and their capabilities."""
    providers = {}
    for provider_name in DEFAULT_CATALOG.list_providers():
        caps = get_capabilities(provider_name)
        models = DEFAULT_CATALOG.list_models(provider_name)
        providers[provider_name] = {
            "models": models,
            "capabilities": {
                "supports_thinking": caps.supports_thinking,
                "supports_reasoning_effort": caps.supports_reasoning_effort,
                "supports_max_output_tokens": caps.supports_max_output_tokens,
                "supports_temperature": caps.supports_temperature,
                "supports_max_retries": caps.supports_max_retries,
            },
            "api_key_configured": bool(get_api_key(provider_name)),
        }
    return {"providers": providers}


@router.get("/llm/models/{provider}")
async def list_llm_models(
    provider: str,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """List available models for a provider."""
    models = DEFAULT_CATALOG.list_models(provider)
    return {
        "provider": provider,
        "models": models,
        "quick_think_suggestion": DEFAULT_CATALOG.suggest_quick_think(provider),
        "deep_think_suggestion": DEFAULT_CATALOG.suggest_deep_think(provider),
    }


@router.post("/llm/client/create")
async def create_llm_client_endpoint(
    request: LLMClientCreateRequest,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Create and validate an LLM client (advisory only)."""
    try:
        # Validate API key is configured
        require_api_key(request.provider)

        # Validate model
        if not validate_model(request.provider, request.model):
            # Warning only — still allow creation
            pass

        client = create_llm_client(
            provider=request.provider,
            model=request.model,
            base_url=request.base_url,
        )

        return {
            "status": "created",
            "provider": request.provider,
            "model": request.model,
            "base_url": request.base_url,
            "provider_name": client.get_provider_name(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/llm/key-status/{provider}")
async def get_llm_key_status(
    provider: str,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Check if an API key is configured for a provider (masked)."""
    key = get_api_key(provider)
    env_var = detect_api_key_env(provider)
    return {
        "provider": provider,
        "configured": bool(key),
        "env_var": env_var,
        "masked_key": mask_api_key(key) if key else None,
    }


# ── Agent Session Management Endpoints ──────────────────────────────────


@router.post("/agents/session", response_model=SessionResponse)
async def create_agent_session(
    request: SessionCreateRequest,
    _principal: PlatformPrincipal,
) -> SessionResponse:
    """Create an authenticated session for an agent.

    Returns a session token that can be used for subsequent authenticated
    requests. The session expires after ttl_seconds.
    """
    rate_limited = not await _agent_rate_limiter.allow_request(request.agent_id)
    if rate_limited:
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    try:
        service = AgentService(StateStore())
        session = service.create_session(request.agent_id, request.ttl_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SessionResponse(
        session_token=session["session_token"],
        agent_id=request.agent_id,
        expires_at=session["expires_at"],
        ttl_seconds=session["ttl_seconds"],
    )


@router.get("/agents/session/validate", response_model=SessionValidateResponse)
async def validate_agent_session(
    session_token: str,
    _principal: PlatformPrincipal,
) -> SessionValidateResponse:
    """Validate a session token and return session info."""
    rate_limited = not await _agent_rate_limiter.allow_request("session_validation")
    if rate_limited:
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    service = AgentService(StateStore())
    session = service.get_session(session_token)
    if session is None:
        return SessionValidateResponse(valid=False)

    return SessionValidateResponse(
        valid=True,
        agent_id=session["agent_id"],
        expires_at=session["expires_at"],
    )


@router.delete("/agents/session")
async def expire_agent_session(
    session_token: str,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Expire (invalidate) a session token."""
    service = AgentService(StateStore())
    expired = service.expire_session(session_token)
    return {"expired": expired}


# ── Agent Rate Limit Status ─────────────────────────────────────────────


@router.get("/agents/rate-limit/{agent_id}")
async def get_agent_rate_limit(
    agent_id: str,
    _principal: PlatformPrincipal,
) -> dict[str, Any]:
    """Get remaining requests for an agent in the current rate limit window."""
    remaining = _agent_rate_limiter.remaining(agent_id)
    return {
        "agent_id": agent_id,
        "remaining": remaining,
        "limit": _agent_rate_limiter.limit,
    }
