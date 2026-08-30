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


def test_agent_os_api_endpoints() -> None:
    # 1. List skills
    skills_res = client.get("/v1/agent-os/skills")
    assert skills_res.status_code == 200
    skills = skills_res.json()
    assert any(s["name"] == "get_market_quote" for s in skills)
    assert any(s["name"] == "submit_guarded_order" for s in skills)

    # 2. Create subaccount
    create_res = client.post(
        "/v1/agent-os/subaccounts",
        json={"agent_name": "api_test_agent", "collateral_usd": 1500.0},
    )
    assert create_res.status_code == 200
    sub_id = create_res.json()["sub_account_id"]
    assert sub_id.startswith("agsub-")

    # 3. List subaccounts
    list_res = client.get("/v1/agent-os/subaccounts")
    assert list_res.status_code == 200
    assert any(a["sub_account_id"] == sub_id for a in list_res.json())

    # 4. Execute skill via API
    exec_res = client.post(
        "/v1/agent-os/execute",
        json={"skill": "get_market_quote", "parameters": {"symbol": "AOT"}},
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["success"] is True
    assert exec_res.json()["result"]["found"] is True
