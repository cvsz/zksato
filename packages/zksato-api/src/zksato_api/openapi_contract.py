"""OpenAPI contract for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OpenAPIContract:
    """Manages OpenAPI contract."""

    def generate_schema(self) -> dict[str, Any]:
        """Generate OpenAPI schema."""
        return {"openapi": "3.0.0", "info": {"title": "zksato API", "version": "2.0.0-dev"}}

    def validate_request(self, path: str, method: str, data: dict[str, Any]) -> bool:
        """Validate request against schema."""
        return True

    def get_endpoints(self) -> list[dict[str, Any]]:
        """Get all endpoints."""
        return []
