from __future__ import annotations

from zksato.domain import Quote, ScannerResult


class MarketScanner:
    """Deterministic quote ranking for dashboard and strategy discovery."""

    def scan(
        self,
        quotes: list[Quote],
        *,
        min_volume: float = 0,
        min_abs_change_pct: float = 0,
        limit: int = 20,
    ) -> list[ScannerResult]:
        results: list[ScannerResult] = []
        max_volume = max((quote.volume for quote in quotes), default=0.0)
        for quote in quotes:
            if quote.volume < min_volume:
                continue
            change = quote.change_pct
            if abs(change) < min_abs_change_pct:
                continue
            volume_score = quote.volume / max_volume if max_volume else 0.0
            momentum_score = min(abs(change) / 10, 1.0)
            score = round((momentum_score * 0.7) + (volume_score * 0.3), 6)
            reasons = [f"change {change:+.2f}%"]
            if volume_score >= 0.5:
                reasons.append("high relative volume")
            results.append(
                ScannerResult(
                    symbol=quote.symbol,
                    last=quote.last,
                    change_pct=change,
                    volume=quote.volume,
                    score=score,
                    reasons=reasons,
                )
            )
        return sorted(results, key=lambda item: (item.score, item.volume), reverse=True)[:limit]
