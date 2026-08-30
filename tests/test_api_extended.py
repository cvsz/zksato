from fastapi.testclient import TestClient

from zksato.api import app

client = TestClient(app)


def test_liveness_readiness_and_request_id() -> None:
    assert client.get("/livez").json() == {"status": "alive"}
    ready = client.get("/readyz")
    assert ready.status_code == 200
    response = client.get("/health", headers={"X-Request-ID": "request-123"})
    assert response.headers["X-Request-ID"] == "request-123"
    generated = client.get("/health")
    assert generated.headers["X-Request-ID"]
    assert generated.headers["X-Request-ID"] != "generated"


def test_market_session_and_research_catalog_endpoints() -> None:
    session = client.get("/v1/market/session")
    assert session.status_code == 200
    assert "timezone" in session.json()

    registered = client.post(
        "/v1/research/strategies/momentum/v1",
        json={
            "name": "momentum",
            "min_history": 3,
            "momentum_period": 2,
            "momentum_threshold_pct": 0.5,
        },
    )
    assert registered.status_code == 200
    catalog = client.get("/v1/research/strategies")
    assert any(item["name"] == "momentum" for item in catalog.json())

    drift = client.post(
        "/v1/research/drift",
        json={
            "expected_return_pct": 5.0,
            "observed_return_pct": 3.5,
            "tolerance_pct_points": 2.0,
        },
    )
    assert drift.status_code == 200
    assert drift.json()["within_tolerance"] is True


def test_order_listing_filters_and_cancel_open_endpoint() -> None:
    client.post(
        "/v1/market/quote",
        json={"symbol": "APIQ", "last": 10.0, "bid": 9.9, "offer": 10.1},
    )
    created = client.post(
        "/v1/orders",
        json={
            "intent": {
                "symbol": "APIQ",
                "side": "buy",
                "quantity": 10,
                "order_type": "limit",
                "price": 9.0,
                "stop_loss": 8.5,
                "client_order_id": "api-open-limit",
            }
        },
    )
    assert created.status_code == 201
    order_id = created.json()["id"]
    detail = client.get(f"/v1/orders/{order_id}")
    assert detail.status_code == 200
    filtered = client.get("/v1/orders", params={"symbol": "APIQ", "status": "accepted"})
    assert any(item["id"] == order_id for item in filtered.json())
    cancelled = client.post("/v1/orders/cancel-open", params={"symbol": "APIQ"})
    assert cancelled.status_code == 200
    assert any(
        item["id"] == order_id and item["status"] == "cancelled" for item in cancelled.json()
    )


def test_video_ea_operator_controls_are_research_paper_only() -> None:
    plan = {
        "symbol": "EAPI",
        "bias": "long",
        "anchor_price": 100.0,
        "atr": 1.0,
        "grid_step": 1.0,
        "triggers": [
            {
                "side": "buy",
                "level": 1,
                "trigger_price": 101.0,
                "quantity": 10,
                "dedupe_key": "eapi-buy-1",
            }
        ],
        "invalidation_price": 98.0,
        "basket_take_profit_r": 1.5,
        "cycle_stop_r": 1.0,
        "max_total_quantity": 10,
        "research_only": True,
        "executable": False,
    }
    armed = client.post(
        "/v1/research/video-ea/arm",
        json={"plan": plan, "current_price": 100.0},
    )
    assert armed.status_code == 200
    assert armed.json()["snapshot"]["state"] == "armed"

    observed = client.post(
        "/v1/research/video-ea/price/EAPI",
        json={"price": 101.5},
    )
    assert observed.status_code == 200
    assert observed.json()["snapshot"]["state"] == "active"

    paused = client.post("/v1/research/video-ea/pause/EAPI")
    assert paused.status_code == 200
    assert paused.json()["snapshot"]["state"] == "paused"
    assert client.get("/v1/research/video-ea/state/EAPI").json()["state"] == "paused"

    reset = client.post("/v1/research/video-ea/reset/EAPI")
    assert reset.status_code == 200
    assert reset.json()["snapshot"]["state"] == "idle"


def test_video_ea_research_analytics_endpoints_return_evidence() -> None:
    candles = [
        {
            "timestamp": f"2026-01-01T00:{index:02d}:00Z",
            "open": 100 + (index % 4),
            "high": 102 + (index % 4),
            "low": 98 + (index % 4),
            "close": 100 + (index % 4),
            "volume": 1000 + index,
        }
        for index in range(24)
    ]
    replay = client.post(
        "/v1/research/video-ea/replay",
        json={
            "symbol": "ANALYTICS",
            "candles": candles,
            "config": {
                "market_profile": "generic_research",
                "grid_mode": "symmetric_research",
                "lookback_bars": 20,
                "levels_per_side": 2,
                "max_total_quantity": 4,
                "max_pending_triggers": 4,
            },
        },
    )
    assert replay.status_code == 200
    assert replay.json()["bars_replayed"] == 24

    sweep = client.post(
        "/v1/research/video-ea/parameter-sweep",
        json={
            "symbol": "ANALYTICS",
            "candles": candles,
            "base_strategy": {"min_history": 5, "fast_period": 2, "slow_period": 4},
            "parameter_grid": {"fast_period": [2, 3], "slow_period": [4]},
            "order_size": 10,
        },
    )
    assert sweep.status_code == 200
    assert sweep.json()["combinations"] == 2

    monte = client.post(
        "/v1/research/video-ea/monte-carlo",
        json={"trade_pnls": [10, -5, 2], "simulations": 20, "seed": 7},
    )
    assert monte.status_code == 200
    assert monte.json()["seed"] == 7


def test_market_terminal_and_status_endpoints() -> None:
    terminal = client.get("/v1/market/terminal")
    assert terminal.status_code == 200
    assert "zksato Market Terminal" in terminal.text
    assert "Content-Security-Policy" in terminal.headers

    tv = client.get("/v1/market/tradingview")
    assert tv.status_code == 200
    assert "zksato TradingView" in tv.text

    hb = client.get("/v1/market/health-bridge")
    assert hb.status_code == 200
    assert "status" in hb.json()
    assert "version" in hb.json()

    ccxt_stat = client.get("/v1/market/ccxt/status")
    assert ccxt_stat.status_code == 200
    assert "running" in ccxt_stat.json()

    pred_stat = client.get("/v1/market/prediction/status")
    assert pred_stat.status_code == 200
    assert "running" in pred_stat.json()
