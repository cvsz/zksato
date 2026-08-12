from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    id: str
    symbol: str
    headline: str
    summary: str
    published_at: datetime
    url: str | None = None
    sentiment_score: float | None = Field(default=None, ge=-1.0, le=1.0)


class NewsAdapter(ABC):
    """Base interface for fetching external news and analyzing sentiment."""

    @abstractmethod
    async def fetch_recent(self, symbol: str, limit: int = 5) -> list[NewsArticle]:
        """Fetch the most recent news articles for a symbol."""
        pass

    @abstractmethod
    async def get_aggregate_sentiment(self, symbol: str) -> float | None:
        """Return an aggregated sentiment score between -1.0 and 1.0."""
        pass


class MockNewsAdapter(NewsAdapter):
    """A simulated news adapter for local testing and paper execution."""

    def __init__(self, override_sentiment: float | None = None):
        self.override_sentiment = override_sentiment

    async def fetch_recent(self, symbol: str, limit: int = 5) -> list[NewsArticle]:
        score = self.override_sentiment if self.override_sentiment is not None else 0.5
        if score > 0:
            headline = "Positive outlook"
        elif score < 0:
            headline = "Negative outlook"
        else:
            headline = "Neutral outlook"
        return [
            NewsArticle(
                id=f"mock-{symbol}-1",
                symbol=symbol,
                headline=f"{headline} for {symbol} in recent quarter",
                summary="Simulated news data for testing sentiment engines.",
                published_at=datetime.now(UTC),
                sentiment_score=score,
            )
        ]

    async def get_aggregate_sentiment(self, symbol: str) -> float | None:
        articles = await self.fetch_recent(symbol)
        scores = [a.sentiment_score for a in articles if a.sentiment_score is not None]
        if not scores:
            return None
        return sum(scores) / len(scores)
