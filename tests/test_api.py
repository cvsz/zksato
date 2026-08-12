# ruff: noqa: I001
from fastapi.testclient import TestClient

from zksato.api import app


client = TestClient(app)


def test_health_and_dashboard() -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "zksato Trading Control" in dashboard.text
    assert "Video EA Research / Paper Cycle" in dashboard.text
    assert "/v1/research/video-ea/pause/" in dashboard.text


def test_quote_ingestion_updates_dashboard() -> None:
    response = client.post(
        "/v1/market/quote",
        json={
            "symbol": "AOT",
            "last": 42.5,
            "bid": 42.25,
            "offer": 42.75,
            "previous_close": 42.0,
            "volume": 10000,
        },
    )
    assert response.status_code == 200
    snapshot = client.get("/v1/dashboard").json()
    assert any(row["symbol"] == "AOT" for row in snapshot["quotes"])


def test_create_price_alert() -> None:
    response = client.post(
        "/v1/alerts",
        json={"symbol": "PTT", "operator": "gte", "price": 35.0},
    )
    assert response.status_code == 201
    assert response.json()["symbol"] == "PTT"
