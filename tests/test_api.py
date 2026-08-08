# ruff: noqa: I001
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from zksato.api import app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    # Keep one TestClient portal/event loop for the module. Async Redis resources
    # are loop-bound and must not be reused across per-request TestClient portals.
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_dashboard(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "zksato Trading Control" in dashboard.text


def test_quote_ingestion_updates_dashboard(client: TestClient) -> None:
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


def test_create_price_alert(client: TestClient) -> None:
    response = client.post(
        "/v1/alerts",
        json={"symbol": "PTT", "operator": "gte", "price": 35.0},
    )
    assert response.status_code == 201
    assert response.json()["symbol"] == "PTT"
