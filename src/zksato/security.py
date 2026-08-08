from __future__ import annotations

from collections import defaultdict, deque
from threading import RLock
from time import monotonic
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from zksato.coordination import CoordinationManager

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "app_secret",
    "authorization",
    "confirmation_token",
    "cookie",
    "csrf",
    "password",
    "pin",
    "secret",
    "session",
    "token",
}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(secret in normalized for secret in SENSITIVE_KEYS):
                result[str(key)] = "[REDACTED]"
            else:
                result[str(key)] = redact_sensitive(item)
        return result
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    return value


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Abuse guard with optional Redis coordination; trading correctness is independent."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 600,
        coordination: CoordinationManager | None = None,
    ) -> None:
        super().__init__(app)
        self.limit = requests_per_minute
        self.coordination = coordination
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in {"/health", "/metrics"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        if self.coordination is not None and self.coordination.redis is not None:
            allowed = await self.coordination.allow_request(
                client,
                limit=self.limit,
                window_seconds=60,
            )
            if not allowed:
                return self._limited()
            return await call_next(request)

        now = monotonic()
        with self._lock:
            events = self._events[client]
            while events and now - events[0] >= 60:
                events.popleft()
            if len(events) >= self.limit:
                return self._limited()
            events.append(now)
        return await call_next(request)

    @staticmethod
    def _limited() -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "rate limit exceeded"},
            headers={"Retry-After": "60"},
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'",
        )
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
