from __future__ import annotations

import hmac
from dataclasses import dataclass
from enum import StrEnum

from fastapi import Header, HTTPException

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


class AuthManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def authenticate(
        self,
        authorization: str | None,
        api_key: str | None,
    ) -> Principal:
        if not self.settings.auth_required:
            return Principal(subject="local-dev", role=Role.PLATFORM_ADMIN)
        token = api_key or self._bearer_token(authorization)
        if not token:
            raise HTTPException(status_code=401, detail="authentication required")
        for configured, role_name in self.settings.api_key_map.items():
            if hmac.compare_digest(configured, token):
                try:
                    role = Role(role_name)
                except ValueError as exc:
                    raise HTTPException(status_code=500, detail="invalid server role mapping") from exc
                return Principal(subject="api-key", role=role)
        raise HTTPException(status_code=401, detail="invalid credentials")

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

    async def dependency(
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> Principal:
        principal = manager.authenticate(authorization, x_api_key)
        return manager.require(principal, required)

    return dependency
