"""Main FastAPI application for zksato."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zksato_core.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="zksato Trading API",
        description="REST API for zksato automated trading platform",
        version="2.0.0-dev",
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
    
    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "zksato-api"}
    
    # Version
    @app.get("/version")
    async def version():
        return {"version": "2.0.0-dev", "name": "zksato"}
    
    return app


# Default app instance
app = create_app()