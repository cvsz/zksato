from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from zksato.notifications.telegram import TelegramNotifier


def test_telegram_notifier_disabled_without_credentials() -> None:
    notifier = TelegramNotifier(bot_token=None, chat_id=None)
    assert notifier.enabled is False


def test_telegram_notifier_enabled_with_credentials() -> None:
    notifier = TelegramNotifier(bot_token="token123", chat_id="chat456")
    assert notifier.enabled is True


@pytest.mark.asyncio
async def test_telegram_send_success() -> None:
    notifier = TelegramNotifier(bot_token="token123", chat_id="chat456")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    with patch("zksato.notifications.telegram.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        result = await notifier.send("hello")
    assert result is True


@pytest.mark.asyncio
async def test_telegram_send_failure_is_silent() -> None:
    notifier = TelegramNotifier(bot_token="token123", chat_id="chat456")
    with patch("zksato.notifications.telegram.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = OSError("network error")
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        result = await notifier.send("hello")
    assert result is False


@pytest.mark.asyncio
async def test_telegram_send_skips_when_disabled() -> None:
    notifier = TelegramNotifier(bot_token=None, chat_id=None)
    result = await notifier.send("hello")
    assert result is False
