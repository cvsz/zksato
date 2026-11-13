"""Market scanner and screening."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from zksato_core.models import ScannerResult

from zksato_market.adapters.base import MarketDataAdapter
from zksato_market.types import Quote


@dataclass
class ScanFilter:
    """Scan filter criteria."""

    min_price: float | None = None
    max_price: float | None = None
    min_volume: int | None = None
    max_volume: int | None = None
    min_change_pct: float | None = None
    max_change_pct: float | None = None
    sectors: list[str] | None = None
    exclude_symbols: list[str] = field(default_factory=list)
    custom_filter: Callable[[Quote], bool] | None = None


class MarketScanner:
    """Market scanner for screening symbols."""

    def __init__(
        self,
        adapter: MarketDataAdapter,
        reference_data: Any = None,
    ) -> None:
        self.adapter = adapter
        self.reference_data = reference_data

    async def scan(
        self,
        symbols: list[str],
        filter_criteria: ScanFilter | None = None,
    ) -> list[ScannerResult]:
        """Scan symbols and return results."""
        filter_criteria = filter_criteria or ScanFilter()
        quotes = await self.adapter.get_quotes(symbols)

        results = []
        for symbol, quote in quotes.items():
            if self._passes_filter(quote, filter_criteria):
                result = self._create_result(symbol, quote)
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _passes_filter(self, quote: Quote, filter_criteria: ScanFilter) -> bool:
        """Check if quote passes filter."""
        if filter_criteria.min_price and quote.last.amount < filter_criteria.min_price:
            return False
        if filter_criteria.max_price and quote.last.amount > filter_criteria.max_price:
            return False
        if filter_criteria.min_volume and quote.volume < filter_criteria.min_volume:
            return False
        if filter_criteria.max_volume and quote.volume > filter_criteria.max_volume:
            return False
        if filter_criteria.min_change_pct and quote.change_pct < filter_criteria.min_change_pct:
            return False
        if filter_criteria.max_change_pct and quote.change_pct > filter_criteria.max_change_pct:
            return False
        if filter_criteria.exclude_symbols and quote.symbol in filter_criteria.exclude_symbols:
            return False
        return not (filter_criteria.custom_filter and not filter_criteria.custom_filter(quote))

    def _create_result(self, symbol: str, quote: Quote) -> ScannerResult:
        """Create scanner result from quote."""
        reasons = []

        if quote.change_pct > 5:
            reasons.append("strong price increase")
        elif quote.change_pct < -5:
            reasons.append("strong price decrease")

        if quote.volume > 1_000_000:
            reasons.append("high volume")

        if quote.spread_pct and quote.spread_pct > 2:
            reasons.append("wide spread")

        score = self._calculate_score(quote)

        return ScannerResult(
            symbol=symbol,
            last=quote.last,
            change_pct=quote.change_pct,
            volume=quote.volume,
            score=score,
            reasons=reasons,
        )

    def _calculate_score(self, quote: Quote) -> float:
        """Calculate scan score (0-1)."""
        score = 0.5

        if quote.change_pct > 0:
            score += min(quote.change_pct / 20, 0.2)
        else:
            score += max(quote.change_pct / 20, -0.2)

        if quote.volume > 100_000:
            score += 0.1

        if quote.spread_pct and quote.spread_pct > 1:
            score -= 0.1

        return max(0.0, min(1.0, score))


class MultiMarketScanner:
    """Scanner that works across multiple markets."""

    def __init__(self) -> None:
        self.scanners: dict[str, MarketScanner] = {}

    def add_scanner(self, name: str, scanner: MarketScanner) -> None:
        """Add a scanner."""
        self.scanners[name] = scanner

    async def scan_all(
        self,
        symbols_by_market: dict[str, list[str]],
        filter_criteria: ScanFilter | None = None,
    ) -> dict[str, list[ScannerResult]]:
        """Scan all markets."""
        results = {}
        for market, symbols in symbols_by_market.items():
            scanner = self.scanners.get(market)
            if scanner:
                results[market] = await scanner.scan(symbols, filter_criteria)
            else:
                results[market] = []
        return results
