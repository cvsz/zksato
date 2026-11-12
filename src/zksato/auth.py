import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any
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


@dataclass
class ApiKey:
    """API key metadata (never stores the raw key value)."""

    key_id: str
    role: str
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    is_active: bool = True
    last_used_at: datetime | None = None
    usage_count: int = 0


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
        self._api_keys: dict[str, ApiKey] = {}
        self._api_key_hashes: dict[str, str] = {}  # hash -> key_id

    def _prune_revoked_sessions(self) -> None:
        now_ts = int(datetime.now(UTC).timestamp())
        expired = [sid for sid, exp in self._session_expiry.items() if exp < now_ts]
        for sid in expired:
            self._revoked_sessions.discard(sid)
            self._session_expiry.pop(sid, None)

    # ── API Key Management ──────────────────────────────────────────────

    def create_api_key(
        self,
        role: str,
        description: str = "",
        ttl_seconds: int | None = None,
    ) -> tuple[str, ApiKey]:
        """Create a new API key.

        Returns the raw key value (shown once) and the ApiKey metadata.
        The raw key is never stored; only its SHA-256 hash is kept.
        """
        key_id = str(uuid4())
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        expires_at: datetime | None = None
        if ttl_seconds is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

        api_key = ApiKey(
            key_id=key_id,
            role=role,
            description=description,
            expires_at=expires_at,
        )
        self._api_keys[key_id] = api_key
        self._api_key_hashes[key_hash] = key_id

        return raw_key, api_key

    def list_api_keys(self) -> list[dict[str, object]]:
        """List all API keys with masked key IDs (no raw values exposed)."""
        now = datetime.now(UTC)
        result: list[dict[str, object]] = []
        for key_id, key in self._api_keys.items():
            expired = key.expires_at is not None and now > key.expires_at
            active = key.is_active and not expired
            # Show only first 8 chars of key_id for identification
            masked_id = key_id[:8] + "..." if len(key_id) > 8 else key_id
            result.append(
                {
                    "key_id": key_id,
                    "masked_id": masked_id,
                    "role": key.role,
                    "description": key.description,
                    "created_at": key.created_at.isoformat(),
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "is_active": active,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                    "usage_count": key.usage_count,
                }
            )
        return sorted(result, key=lambda k: str(k["created_at"]), reverse=True)

    def get_api_key(self, key_id: str) -> ApiKey | None:
        """Get API key metadata by key ID."""
        return self._api_keys.get(key_id)

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke (deactivate) an API key. Returns True if found and revoked."""
        api_key = self._api_keys.get(key_id)
        if api_key is None:
            return False
        api_key.is_active = False
        return True

    def _lookup_api_key_by_hash(self, key_hash: str) -> str | None:
        """Look up key_id by SHA-256 hash of the raw key."""
        return self._api_key_hashes.get(key_hash)

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
        # First check statically configured API keys from settings
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

        # Then check dynamically managed API keys
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        key_id = self._lookup_api_key_by_hash(key_hash)
        if key_id is not None:
            api_key = self._api_keys.get(key_id)
            if api_key is not None:
                now = datetime.now(UTC)
                if not api_key.is_active:
                    raise HTTPException(status_code=401, detail="api key revoked")
                if api_key.expires_at is not None and now > api_key.expires_at:
                    raise HTTPException(status_code=401, detail="api key expired")
                # Update usage stats
                api_key.last_used_at = now
                api_key.usage_count += 1
                try:
                    role = Role(api_key.role)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=500,
                        detail="invalid server role mapping",
                    ) from exc
                digest = key_hash[:16]
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


def require_roles(manager: AuthManager, *roles: Role) -> Any:
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
