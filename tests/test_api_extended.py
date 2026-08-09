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
