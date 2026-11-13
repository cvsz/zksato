"""Main FastAPI application for zksato."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from zksato_core.config import Settings

from zksato_api.dashboard import (
    start_periodic_broadcast,
    stop_periodic_broadcast,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifespan handler."""
    # Startup
    await start_periodic_broadcast()
    yield
    # Shutdown
    await stop_periodic_broadcast()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="zksato Trading API",
        description="REST API for zksato automated trading platform",
        version="2.0.0-dev",
        lifespan=lifespan,
    )

    # CORS
    if settings and settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Include dashboard router
    from zksato_api.dashboard import router as dashboard_router

    app.include_router(dashboard_router)

    # Health check
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "zksato-api"}

    # Version
    @app.get("/version")
    async def version() -> dict[str, str]:
        return {"version": "2.0.0-dev", "name": "zksato"}

    return app


# Default app instance
app = create_app()
