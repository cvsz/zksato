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
