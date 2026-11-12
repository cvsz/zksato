"""Market terminal for zksato."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MarketTerminal:
    """Market data terminal."""
    
    def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get quote for a symbol."""
        return {"symbol": symbol, "bid": 0, "ask": 0, "last": 0}
    
    def get_depth(self, symbol: str) -> dict[str, Any]:
        """Get market depth."""
        return {"symbol": symbol, "bids": [], "asks": []}
    
    def get_trades(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent trades."""
        return []