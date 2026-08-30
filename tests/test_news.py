from __future__ import annotations

import pytest

from zksato.news import MockNewsAdapter, NewsAdapter, NewsArticle


def test_news_article_model_validates_sentiment_range() -> None:
    article = NewsArticle(
        id="art-1",
        symbol="AOT",
        headline="AOT rises 2%",
        summary="Strong quarter",
        published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        sentiment_score=0.75,
    )
    assert article.sentiment_score == 0.75

    with pytest.raises(Exception):  # noqa: B017
        NewsArticle(
            id="bad",
            symbol="AOT",
            headline="h",
            summary="s",
            published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            sentiment_score=1.5,  # out of range
        )


@pytest.mark.asyncio
async def test_mock_news_adapter_returns_positive_sentiment() -> None:
    adapter = MockNewsAdapter(override_sentiment=0.8)
    articles = await adapter.fetch_recent("AOT")
    assert len(articles) == 1
    assert articles[0].symbol == "AOT"
    assert articles[0].sentiment_score == 0.8
    assert "Positive" in articles[0].headline


@pytest.mark.asyncio
async def test_mock_news_adapter_returns_negative_sentiment() -> None:
    adapter = MockNewsAdapter(override_sentiment=-0.6)
    articles = await adapter.fetch_recent("PTT")
    assert articles[0].sentiment_score == -0.6
    assert "Negative" in articles[0].headline


@pytest.mark.asyncio
async def test_mock_news_adapter_returns_neutral_sentiment() -> None:
    adapter = MockNewsAdapter(override_sentiment=0.0)
    articles = await adapter.fetch_recent("KBANK")
    assert articles[0].sentiment_score == 0.0
    assert "Neutral" in articles[0].headline


@pytest.mark.asyncio
async def test_mock_news_aggregate_sentiment_equals_fetch_score() -> None:
    adapter = MockNewsAdapter(override_sentiment=0.5)
    score = await adapter.get_aggregate_sentiment("AOT")
    assert score == 0.5


@pytest.mark.asyncio
async def test_news_adapter_is_abstract() -> None:
    """NewsAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        NewsAdapter()  # type: ignore[abstract]
