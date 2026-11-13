import pytest
from fastapi import HTTPException

from zksato.auth import AuthManager, Principal, Role
from zksato.config import Settings


def test_auth_manager_maps_api_key_to_role() -> None:
    manager = AuthManager(
        Settings(auth_required=True, api_keys="reader:read_only;ops:order_approver")
    )
    principal = manager.authenticate(None, "ops")
    assert principal.role == Role.ORDER_APPROVER
    assert manager.require(principal, {Role.STRATEGY_OPERATOR}) == principal


def test_auth_manager_rejects_invalid_key() -> None:
    manager = AuthManager(Settings(auth_required=True, api_keys="reader:read_only"))
    with pytest.raises(HTTPException) as exc_info:
        manager.authenticate(None, "wrong")
    assert exc_info.value.status_code == 401


def test_platform_admin_grants_all_roles() -> None:
    manager = AuthManager(Settings(auth_required=False))
    principal = Principal("local", Role.PLATFORM_ADMIN)
    assert manager.require(principal, {Role.RISK_ADMIN}) == principal


# ── API Key Management Tests ───────────────────────────────────────────


def test_create_api_key_returns_raw_key_once() -> None:
    manager = AuthManager(Settings(auth_required=True))
    raw_key, api_key = manager.create_api_key(role="risk_admin", description="test key")
    assert raw_key is not None
    assert len(raw_key) > 0
    assert api_key.key_id is not None
    assert api_key.role == "risk_admin"
    assert api_key.description == "test key"
    assert api_key.is_active is True
    assert api_key.usage_count == 0


def test_authenticate_with_dynamic_api_key() -> None:
    manager = AuthManager(Settings(auth_required=True))
    raw_key, _ = manager.create_api_key(role="read_only", description="dynamic key")
    principal = manager.authenticate(None, raw_key)
    assert principal.role == Role.READ_ONLY
    assert principal.subject.startswith("api-key:")


def test_authenticate_revoked_api_key_rejected() -> None:
    manager = AuthManager(Settings(auth_required=True))
    raw_key, api_key = manager.create_api_key(role="read_only")
    manager.revoke_api_key(api_key.key_id)
    with pytest.raises(HTTPException) as exc_info:
        manager.authenticate(None, raw_key)
    assert exc_info.value.status_code == 401


def test_authenticate_expired_api_key_rejected() -> None:
    manager = AuthManager(Settings(auth_required=True))
    raw_key, _api_key = manager.create_api_key(
        role="read_only", ttl_seconds=-1
    )  # Immediately expired
    with pytest.raises(HTTPException) as exc_info:
        manager.authenticate(None, raw_key)
    assert exc_info.value.status_code == 401


def test_list_api_keys_returns_metadata() -> None:
    manager = AuthManager(Settings(auth_required=True))
    _, _key1 = manager.create_api_key(role="read_only", description="first")
    _, _key2 = manager.create_api_key(role="risk_admin", description="second")
    keys = manager.list_api_keys()
    assert len(keys) == 2
    roles = {k["role"] for k in keys}
    assert roles == {"read_only", "risk_admin"}
    # Raw key values should never be in the list
    for k in keys:
        assert "raw_key" not in k


def test_revoke_nonexistent_key_returns_false() -> None:
    manager = AuthManager(Settings(auth_required=True))
    result = manager.revoke_api_key("nonexistent-key-id")
    assert result is False


def test_api_key_usage_count_increments() -> None:
    manager = AuthManager(Settings(auth_required=True))
    raw_key, api_key = manager.create_api_key(role="read_only")
    assert api_key.usage_count == 0
    manager.authenticate(None, raw_key)
    updated = manager.get_api_key(api_key.key_id)
    assert updated is not None
    assert updated.usage_count == 1


def test_get_nonexistent_api_key_returns_none() -> None:
    manager = AuthManager(Settings(auth_required=True))
    result = manager.get_api_key("nonexistent-key-id")
    assert result is None
