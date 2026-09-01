import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated
from uuid import uuid4

from fastapi import Cookie, Header, HTTPException, Request

from zksato.config import Settings


class Role(StrEnum):
    READ_ONLY = "read_only"
    STRATEGY_OPERATOR = "strategy_operator"
    ORDER_APPROVER = "order_approver"
    RISK_ADMIN = "risk_admin"
    PLATFORM_ADMIN = "platform_admin"
    AUDITOR = "auditor"


ROLE_GRANTS: dict[Role, set[Role]] = {
    Role.READ_ONLY: {Role.READ_ONLY},
    Role.STRATEGY_OPERATOR: {Role.READ_ONLY, Role.STRATEGY_OPERATOR},
    Role.ORDER_APPROVER: {
        Role.READ_ONLY,
        Role.STRATEGY_OPERATOR,
        Role.ORDER_APPROVER,
    },
    Role.RISK_ADMIN: {
        Role.READ_ONLY,
        Role.STRATEGY_OPERATOR,
        Role.ORDER_APPROVER,
        Role.RISK_ADMIN,
    },
    Role.AUDITOR: {Role.READ_ONLY, Role.AUDITOR},
    Role.PLATFORM_ADMIN: set(Role),
}


@dataclass(frozen=True)
class Principal:
    subject: str
    role: Role
    auth_method: str = "api_key"
    session_id: str | None = None
    csrf_token: str | None = None


@dataclass(frozen=True)
class IssuedSession:
    token: str
    csrf_token: str
    expires_at: datetime
    principal: Principal


class AuthManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._revoked_sessions: set[str] = set()
        self._session_expiry: dict[str, int] = {}

    def _prune_revoked_sessions(self) -> None:
        now_ts = int(datetime.now(UTC).timestamp())
        expired = [sid for sid, exp in self._session_expiry.items() if exp < now_ts]
        for sid in expired:
            self._revoked_sessions.discard(sid)
            self._session_expiry.pop(sid, None)

    def authenticate(
        self,
        authorization: str | None,
        api_key: str | None,
        *,
        session_token: str | None = None,
        csrf_token: str | None = None,
        method: str = "GET",
    ) -> Principal:
        if not self.settings.auth_required:
            return Principal(subject="local-dev", role=Role.PLATFORM_ADMIN, auth_method="local")
        token = api_key or self._bearer_token(authorization)
        if token:
            return self._authenticate_api_key(token)
        if session_token:
            principal = self._authenticate_session(session_token)
            if self.settings.csrf_required and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
                if not csrf_token or not principal.csrf_token:
                    raise HTTPException(status_code=403, detail="CSRF token required")
                if not hmac.compare_digest(csrf_token, principal.csrf_token):
                    raise HTTPException(status_code=403, detail="invalid CSRF token")
            return principal
        raise HTTPException(status_code=401, detail="authentication required")

    def _authenticate_api_key(self, token: str) -> Principal:
        for configured, role_name in self.settings.api_key_map.items():
            if hmac.compare_digest(configured, token):
                try:
                    role = Role(role_name)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=500,
                        detail="invalid server role mapping",
                    ) from exc
                digest = hashlib.sha256(token.encode()).hexdigest()[:16]
                return Principal(subject=f"api-key:{digest}", role=role)
        raise HTTPException(status_code=401, detail="invalid credentials")

    def issue_session(self, authorization: str | None, api_key: str | None) -> IssuedSession:
        if not self.settings.session_secret:
            raise HTTPException(status_code=409, detail="server session secret is not configured")
        principal = self.authenticate(authorization, api_key)
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self.settings.session_ttl_seconds)
        session_id = str(uuid4())
        csrf = secrets.token_urlsafe(32)
        payload = {
            "sub": principal.subject,
            "role": principal.role.value,
            "sid": session_id,
            "csrf": csrf,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        encoded = self._b64url(json.dumps(payload, separators=(",", ":")).encode())
        signature = self._sign(encoded)
        token = f"{encoded}.{signature}"
        return IssuedSession(
            token=token,
            csrf_token=csrf,
            expires_at=expires_at,
            principal=Principal(
                subject=principal.subject,
                role=principal.role,
                auth_method="session",
                session_id=session_id,
                csrf_token=csrf,
            ),
        )

    def revoke_session(self, token: str) -> None:
        payload = self._decode_session(token)
        session_id = str(payload.get("sid", ""))
        if session_id:
            self._revoked_sessions.add(session_id)
            raw_exp = payload.get("exp", 0)
            self._session_expiry[session_id] = int(raw_exp) if isinstance(raw_exp, int) else 0

    def _authenticate_session(self, token: str) -> Principal:
        self._prune_revoked_sessions()
        payload = self._decode_session(token)
        session_id = str(payload.get("sid", ""))
        if not session_id or session_id in self._revoked_sessions:
            raise HTTPException(status_code=401, detail="session revoked")
        try:
            role = Role(str(payload["role"]))
            subject = str(payload["sub"])
            raw_expiry = payload["exp"]
            if not isinstance(raw_expiry, (int, str)):
                raise TypeError("invalid expiry type")
            expiry = int(raw_expiry)
            csrf = str(payload["csrf"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=401, detail="invalid session") from exc
        if expiry <= int(datetime.now(UTC).timestamp()):
            raise HTTPException(status_code=401, detail="session expired")
        return Principal(
            subject=subject,
            role=role,
            auth_method="session",
            session_id=session_id,
            csrf_token=csrf,
        )

    def _decode_session(self, token: str) -> dict[str, object]:
        if not self.settings.session_secret:
            raise HTTPException(status_code=401, detail="sessions are disabled")
        encoded, separator, signature = token.partition(".")
        if not separator or not signature:
            raise HTTPException(status_code=401, detail="invalid session")
        expected = self._sign(encoded)
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="invalid session signature")
        try:
            decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            payload = json.loads(decoded)
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=401, detail="invalid session") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=401, detail="invalid session")
        return payload

    def _sign(self, encoded: str) -> str:
        secret = self.settings.session_secret
        if not secret:
            raise HTTPException(status_code=409, detail="server session secret is not configured")
        digest = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).digest()
        return self._b64url(digest)

    @staticmethod
    def _b64url(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    @staticmethod
    def _bearer_token(authorization: str | None) -> str | None:
        if not authorization:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        return token.strip()

    def require(self, principal: Principal, roles: set[Role]) -> Principal:
        granted = ROLE_GRANTS[principal.role]
        if not roles.intersection(granted):
            raise HTTPException(status_code=403, detail="insufficient role")
        return principal


def require_roles(manager: AuthManager, *roles: Role):
    required = set(roles)
    cookie_alias = manager.settings.session_cookie_name

    async def dependency(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
        x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
        session_token: Annotated[str | None, Cookie(alias=cookie_alias)] = None,
    ) -> Principal:
        principal = manager.authenticate(
            authorization,
            x_api_key,
            session_token=session_token,
            csrf_token=x_csrf_token,
            method=request.method,
        )
        return manager.require(principal, required)

    return dependency
