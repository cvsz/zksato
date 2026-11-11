"""
Pairlist management for trading strategies.

Pairlists determine which trading pairs are eligible for trading.
Inspired by Freqtrade's pairlist system. Supports static whitelists,
blacklists, and dynamic pairlist providers.

Pairlists are advisory — they filter which symbols strategies can
generate signals for, but all orders still route through RiskEngine.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PairInfo:
    """Information about a trading pair."""

    symbol: str
    exchange: str = ""
    active: bool = True
    stake_currency: str = "USDT"
    volume_24h: float = 0.0
    price: float = 0.0
    change_pct_24h: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class PairList(ABC):
    """Base class for pairlist providers."""

    name: str = "BasePairList"

    @abstractmethod
    def filter_pairs(
        self,
        pairs: list[PairInfo],
        context: dict[str, Any] | None = None,
    ) -> list[PairInfo]:
        """Filter and return the list of tradeable pairs."""
        ...


class StaticPairList(PairList):
    """Static whitelist/blacklist pairlist.

    Uses a configured whitelist (pairs to trade) and blacklist
    (pairs to avoid).
    """

    name = "StaticPairList"

    def __init__(
        self,
        whitelist: list[str] | None = None,
        blacklist: list[str] | None = None,
    ) -> None:
        self.whitelist = set(whitelist or [])
        self.blacklist = set(blacklist or [])

    def filter_pairs(
        self,
        pairs: list[PairInfo],
        context: dict[str, Any] | None = None,
    ) -> list[PairInfo]:
        filtered = []
        for pair in pairs:
            # Blacklist takes precedence
            if pair.symbol in self.blacklist:
                logger.debug("Pair %s filtered by blacklist", pair.symbol)
                continue
            # If whitelist is set, only whitelisted pairs pass
            if self.whitelist and pair.symbol not in self.whitelist:
                logger.debug("Pair %s filtered (not in whitelist)", pair.symbol)
                continue
            filtered.append(pair)
        return filtered


class VolumePairList(PairList):
    """Dynamic pairlist based on 24h volume ranking."""

    name = "VolumePairList"

    def __init__(
        self,
        number_assets: int = 50,
        sort_by: str = "volume_24h",
        min_volume: float = 0.0,
    ) -> None:
        self.number_assets = number_assets
        self.sort_by = sort_by
        self.min_volume = min_volume

    def filter_pairs(
        self,
        pairs: list[PairInfo],
        context: dict[str, Any] | None = None,
    ) -> list[PairInfo]:
        # Filter by minimum volume
        filtered = [p for p in pairs if p.volume_24h >= self.min_volume]

        # Sort by the specified field
        if self.sort_by in ("volume_24h", "change_pct_24h"):
            filtered.sort(key=lambda p: getattr(p, self.sort_by, 0), reverse=True)
        else:
            filtered.sort(key=lambda p: getattr(p, self.sort_by, 0))

        # Take top N
        return filtered[: self.number_assets]


class ChangePctPairList(PairList):
    """Dynamic pairlist based on 24h price change percentage."""

    name = "ChangePctPairList"

    def __init__(
        self,
        number_assets: int = 50,
        min_change_pct: float = 0.0,
        max_change_pct: float | None = None,
    ) -> None:
        self.number_assets = number_assets
        self.min_change_pct = min_change_pct
        self.max_change_pct = max_change_pct

    def filter_pairs(
        self,
        pairs: list[PairInfo],
        context: dict[str, Any] | None = None,
    ) -> list[PairInfo]:
        filtered = []
        for pair in pairs:
            change = pair.change_pct_24h
            if change < self.min_change_pct:
                continue
            if self.max_change_pct is not None and change > self.max_change_pct:
                continue
            filtered.append(pair)

        filtered.sort(key=lambda p: p.change_pct_24h, reverse=True)
        return filtered[: self.number_assets]


class PairListManager:
    """Manages pairlist providers and applies them to filter tradeable pairs."""

    def __init__(
        self,
        pairlist: PairList | None = None,
    ) -> None:
        self.pairlist = pairlist

    def set_pairlist(self, pairlist: PairList) -> None:
        self.pairlist = pairlist

    def filter_pairs(
        self,
        pairs: list[PairInfo],
        context: dict[str, Any] | None = None,
    ) -> list[PairInfo]:
        if self.pairlist is None:
            return pairs
        return self.pairlist.filter_pairs(pairs, context)

    def is_tradeable(
        self,
        symbol: str,
        pairs: list[PairInfo],
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Check if a symbol is tradeable according to the pairlist."""
        filtered = self.filter_pairs(pairs, context)
        return any(p.symbol == symbol for p in filtered)
