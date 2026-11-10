import pytest
from fastapi.testclient import TestClient

from zksato.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_admin_env_endpoints(client, monkeypatch, tmp_path):
    test_env = tmp_path / ".env"
    test_env.write_text("ZKSATO_TEST_VAR=123\nZKSATO_TEST_SECRET=supersecret\n", encoding="utf-8")
    monkeypatch.setattr("zksato.api.ENV_PATH", test_env)

    # 1. GET /v1/admin/env (auth is disabled in test mode / paper by default or platform_admin)
    res = client.get("/v1/admin/env")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "raw" in data

    items_map = {item["key"]: item for item in data["items"]}
    assert "ZKSATO_TEST_VAR" in items_map
    assert items_map["ZKSATO_TEST_VAR"]["value"] == "123"
    assert items_map["ZKSATO_TEST_VAR"]["is_secret"] is False

    assert "ZKSATO_TEST_SECRET" in items_map
    assert items_map["ZKSATO_TEST_SECRET"]["value"] == "********"
    assert items_map["ZKSATO_TEST_SECRET"]["is_secret"] is True

    # 2. POST /v1/admin/env updates key
    res_update = client.post(
        "/v1/admin/env",
        json={"ZKSATO_TEST_VAR": "456", "ZKSATO_NEW_SETTING": "new_val"},
    )
    assert res_update.status_code == 200
    updated_text = test_env.read_text(encoding="utf-8")
    assert "ZKSATO_TEST_VAR=456" in updated_text
    assert "ZKSATO_NEW_SETTING=new_val" in updated_text
    # Secret with placeholder ******** must NOT overwrite actual secret
    client.post("/v1/admin/env", json={"ZKSATO_TEST_SECRET": "********"})
    assert "ZKSATO_TEST_SECRET=supersecret" in test_env.read_text(encoding="utf-8")

    # 3. POST /v1/admin/env/raw
    res_raw = client.post(
        "/v1/admin/env/raw",
        json={"content": "CUSTOM_RAW_KEY=999\n"},
    )
    assert res_raw.status_code == 200
    assert test_env.read_text(encoding="utf-8") == "CUSTOM_RAW_KEY=999\n"
