from __future__ import annotations

from collections import defaultdict, deque
from threading import RLock
from time import monotonic

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-process abuse guard; durable trading correctness does not depend on it."""

    def __init__(self, app, requests_per_minute: int = 600) -> None:
        super().__init__(app)
        self.limit = requests_per_minute
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in {"/health", "/metrics"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = monotonic()
        with self._lock:
            events = self._events[client]
            while events and now - events[0] >= 60:
                events.popleft()
            if len(events) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
            events.append(now)
        return await call_next(request)


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
        return response
