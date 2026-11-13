"""API client for zksato TUI.

Communicates with the zksato FastAPI backend on port 9569.
All requests go through the REST API which enforces RiskEngine
and TradingService boundaries.
"""

from __future__ import annotations

from typing import Any

import httpx


class ZKSATOAPIClient:
    """HTTP client for zksato API."""

    def __init__(self, base_url: str = "http://localhost:9569", api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health(self) -> dict[str, Any]:
        """Check API health."""
        client = await self._get_client()
        resp = await client.get("/health")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def version(self) -> dict[str, Any]:
        """Get API version."""
        client = await self._get_client()
        resp = await client.get("/version")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def get_market_quote(self, symbol: str) -> dict[str, Any]:
        """Get a market quote for a symbol."""
        client = await self._get_client()
        resp = await client.post(
            "/v1/market/quote",
            json={
                "symbol": symbol,
                "last": 0.0,
                "bid": 0.0,
                "offer": 0.0,
                "previous_close": 0.0,
                "volume": 0,
            },
        )
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def list_quotes(self) -> list[dict[str, Any]]:
        """List all market quotes."""
        client = await self._get_client()
        resp = await client.get("/v1/market/quotes")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio snapshot."""
        client = await self._get_client()
        resp = await client.get("/v1/portfolio")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def get_orders(self) -> list[dict[str, Any]]:
        """List orders."""
        client = await self._get_client()
        resp = await client.get("/v1/orders")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def get_risk_evaluations(self) -> list[dict[str, Any]]:
        """Get risk evaluations."""
        client = await self._get_client()
        resp = await client.get("/v1/risk/evaluations")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def submit_order(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """Submit an order intent. Routes through RiskEngine."""
        client = await self._get_client()
        resp = await client.post("/v1/orders", json={"intent": order_data})
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an order."""
        client = await self._get_client()
        resp = await client.delete(f"/v1/orders/{order_id}")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def get_agent_sessions(self) -> list[dict[str, Any]]:
        """List agent sessions."""
        client = await self._get_client()
        resp = await client.get("/v1/agent-sessions")
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]

    async def create_agent_session(self, session_data: dict[str, Any]) -> dict[str, Any]:
        """Create an agent session."""
        client = await self._get_client()
        resp = await client.post("/v1/agent-sessions", json=session_data)
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]
