"""Pairlist management for multi-symbol trading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PairInfo:
    """Information about a trading pair."""

    symbol: str
    volume_24h: float = 0.0
    price_change_24h: float = 0.0
    spread_pct: float = 0.0
    liquidity_score: float = 0.0
    volatility: float = 0.0
    enabled: bool = True
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PairListManager:
    """Manages trading pair lists with filtering and ranking."""

    def __init__(self) -> None:
        self._pairs: dict[str, PairInfo] = {}
        self._whitelist: set[str] = set()
        self._blacklist: set[str] = set()

    def add_pair(self, pair: PairInfo) -> None:
        """Add or update a pair."""
        self._pairs[pair.symbol] = pair

    def add_pairs(self, pairs: list[PairInfo]) -> None:
        """Add multiple pairs."""
        for pair in pairs:
            self.add_pair(pair)

    def remove_pair(self, symbol: str) -> bool:
        """Remove a pair."""
        if symbol in self._pairs:
            del self._pairs[symbol]
            return True
        return False

    def get_pair(self, symbol: str) -> PairInfo | None:
        """Get pair info."""
        return self._pairs.get(symbol)

    def get_all_pairs(self) -> list[PairInfo]:
        """Get all pairs."""
        return list(self._pairs.values())

    def get_enabled_pairs(self) -> list[PairInfo]:
        """Get enabled pairs (not blacklisted, whitelisted if whitelist exists)."""
        pairs = []
        for pair in self._pairs.values():
            if not pair.enabled:
                continue
            if pair.symbol in self._blacklist:
                continue
            if self._whitelist and pair.symbol not in self._whitelist:
                continue
            pairs.append(pair)
        return pairs

    def set_whitelist(self, symbols: list[str]) -> None:
        """Set whitelist - only these symbols will be enabled."""
        self._whitelist = set(symbols)

    def set_blacklist(self, symbols: list[str]) -> None:
        """Set blacklist - these symbols will be disabled."""
        self._blacklist = set(symbols)

    def filter_by_volume(self, min_volume: float) -> list[PairInfo]:
        """Filter pairs by minimum 24h volume."""
        return [p for p in self.get_enabled_pairs() if p.volume_24h >= min_volume]

    def filter_by_spread(self, max_spread_pct: float) -> list[PairInfo]:
        """Filter pairs by maximum spread percentage."""
        return [p for p in self.get_enabled_pairs() if p.spread_pct <= max_spread_pct]

    def filter_by_volatility(self, min_vol: float, max_vol: float) -> list[PairInfo]:
        """Filter pairs by volatility range."""
        return [p for p in self.get_enabled_pairs() if min_vol <= p.volatility <= max_vol]

    def rank_by_liquidity(self, top_n: int | None = None) -> list[PairInfo]:
        """Rank pairs by liquidity score."""
        pairs = sorted(self.get_enabled_pairs(), key=lambda p: p.liquidity_score, reverse=True)
        return pairs[:top_n] if top_n else pairs

    def rank_by_volatility(self, top_n: int | None = None) -> list[PairInfo]:
        """Rank pairs by volatility (highest first)."""
        pairs = sorted(self.get_enabled_pairs(), key=lambda p: p.volatility, reverse=True)
        return pairs[:top_n] if top_n else pairs

    def update_market_data(
        self,
        symbol: str,
        volume_24h: float | None = None,
        price_change_24h: float | None = None,
        spread_pct: float | None = None,
    ) -> None:
        """Update market data for a pair."""
        if symbol in self._pairs:
            pair = self._pairs[symbol]
            if volume_24h is not None:
                pair.volume_24h = volume_24h
            if price_change_24h is not None:
                pair.price_change_24h = price_change_24h
            if spread_pct is not None:
                pair.spread_pct = spread_pct
            # Recalculate liquidity score
            pair.liquidity_score = pair.volume_24h / (1 + pair.spread_pct * 100)

    def enable_symbol(self, symbol: str) -> bool:
        """Enable a symbol."""
        if symbol in self._pairs:
            self._pairs[symbol].enabled = True
            return True
        return False

    def disable_symbol(self, symbol: str) -> bool:
        """Disable a symbol."""
        if symbol in self._pairs:
            self._pairs[symbol].enabled = False
            return True
        return False
