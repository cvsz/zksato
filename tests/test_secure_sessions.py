import pytest
from fastapi import HTTPException

from zksato.auth import AuthManager, Role
from zksato.config import Settings


def test_signed_session_auth_and_csrf() -> None:
    settings = Settings(
        auth_required=True,
        api_keys="api-secret:risk_admin",
        session_secret="session-secret-that-is-long-enough",
        csrf_required=True,
    )
    manager = AuthManager(settings)
    issued = manager.issue_session(None, "api-secret")
    principal = manager.authenticate(
        None,
        None,
        session_token=issued.token,
        csrf_token=issued.csrf_token,
        method="POST",
    )
    assert principal.role == Role.RISK_ADMIN
    assert principal.auth_method == "session"

    with pytest.raises(HTTPException, match="invalid CSRF"):
        manager.authenticate(
            None,
            None,
            session_token=issued.token,
            csrf_token="wrong",
            method="POST",
        )

    manager.revoke_session(issued.token)
    with pytest.raises(HTTPException, match="revoked"):
        manager.authenticate(None, None, session_token=issued.token, method="GET")
