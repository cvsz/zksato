from __future__ import annotations

from typing import Any

from zksato.llm_clients.api_key_env import require_api_key
from zksato.llm_clients.base_client import BaseLLMClient
from zksato.llm_clients.openai_client import (
    AnthropicClient,
    AzureOpenAIClient,
    BedrockClient,
    GoogleClient,
    OpenAIClient,
    is_openai_compatible,
)


def create_llm_client(
    provider: str,
    model: str,
    base_url: str | None = None,
    **kwargs: Any,
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: LLM provider name (e.g. ``openai``, ``anthropic``, ``google``,
            ``azure``, ``bedrock``, ``openrouter``).
        model: Model name/identifier.
        base_url: Optional base URL for API endpoint.
        **kwargs: Additional provider-specific arguments (temperature,
            max_retries, max_tokens, reasoning_effort, thinking_level, etc.).

    Returns:
        Configured LLM client instance.

    Raises:
        ValueError: If provider is not supported or API key is missing.
    """
    provider_lower = provider.lower()

    # Native (non-OpenAI-compatible) APIs matched first so their string check
    # doesn't import the OpenAI client. Everything else routes through the
    # OpenAI-compatible client.
    if provider_lower == "anthropic":
        return AnthropicClient(model, base_url, **kwargs)

    if provider_lower == "google":
        return GoogleClient(model, base_url, **kwargs)

    if provider_lower == "azure":
        return AzureOpenAIClient(model, base_url, **kwargs)

    if provider_lower == "bedrock":
        return BedrockClient(model, base_url, **kwargs)

    if is_openai_compatible(provider_lower):
        return OpenAIClient(model, base_url, provider=provider_lower, **kwargs)

    raise ValueError(f"Unsupported LLM provider: {provider}")


def build_llm_kwargs(
    config: dict[str, Any],
    provider: str | None = None,
) -> dict[str, Any]:
    """Build keyword arguments for ``create_llm_client`` from a config dict.

    Cross-provider settings (temperature, max_retries, max_tokens) are
    forwarded when set. Provider-specific settings (reasoning_effort for
    OpenAI/Azure, thinking_level for Google, effort for Anthropic) are
    forwarded for the matching provider.

    Args:
        config: Configuration dictionary with keys like ``llm_provider``,
            ``temperature``, ``max_retries``, ``max_tokens``,
            ``reasoning_effort``, ``thinking_level``, ``effort``.
        provider: Optional provider name for provider-specific settings.
            Defaults to ``config["llm_provider"]``.

    Returns:
        Keyword arguments suitable for ``create_llm_client``.
    """
    kwargs: dict[str, Any] = {}
    provider = (provider or config.get("llm_provider", "")).lower()

    # Provider-specific reasoning/thinking knobs
    if provider == "google":
        thinking_level = config.get("google_thinking_level")
        if thinking_level:
            kwargs["thinking_level"] = thinking_level
    elif provider in ("openai", "chatgpt", "azure"):
        reasoning_effort = config.get("reasoning_effort") or config.get("openai_reasoning_effort")
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
    elif provider == "anthropic":
        effort = config.get("anthropic_effort") or config.get("effort")
        if effort:
            kwargs["effort"] = effort

    # Cross-provider: temperature
    temperature = config.get("temperature")
    if temperature is not None and temperature != "":
        kwargs["temperature"] = float(temperature)

    # Cross-provider: SDK retry budget
    max_retries = config.get("max_retries") or config.get("llm_max_retries")
    if max_retries is not None and max_retries != "":
        kwargs["max_retries"] = _coerce_max_retries(max_retries)

    # Cross-provider: output-token cap (Gemini names it max_output_tokens)
    max_tokens = config.get("max_tokens") or config.get("max_output_tokens")
    if max_tokens is not None and max_tokens != "":
        key = "max_output_tokens" if provider == "google" else "max_tokens"
        kwargs[key] = _coerce_max_tokens(max_tokens)

    return kwargs


def _coerce_max_retries(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"max_retries must be an integer, not a boolean: {value!r}")
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"max_retries must be an integer, got {value!r}") from exc
    if n < 0:
        raise ValueError(f"max_retries must be >= 0, got {n}")
    return n


def _coerce_max_tokens(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"max_tokens must be an integer, not a boolean: {value!r}")
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"max_tokens must be an integer, got {value!r}") from exc
    if n <= 0:
        raise ValueError(f"max_tokens must be > 0, got {n}")
    return n


def tier_provider(config: dict[str, Any], tier: str) -> str:
    """The provider of the ``quick`` or ``deep`` model tier: its own, else ``llm_provider``."""
    provider = config.get(f"{tier}_think_provider") or config.get("llm_provider", "openai")
    return str(provider).lower()


def create_tier_client(
    config: dict[str, Any],
    tier: str,
    **extra: Any,
) -> BaseLLMClient:
    """Create the LLM client for the ``quick`` or ``deep`` model tier.

    A tier on its own provider gets that provider's settings (thinking level,
    reasoning effort, output-token cap) and its own endpoint, else the
    provider's default: ``backend_url`` belongs to ``llm_provider``.

    Args:
        config: Configuration dictionary.
        tier: Either ``"quick"`` or ``"deep``.
        **extra: Additional keyword arguments passed to ``create_llm_client``.

    Returns:
        Configured LLM client instance.
    """
    provider = tier_provider(config, tier)
    llm_provider = config.get("llm_provider", "openai").lower()

    if provider == llm_provider:
        base_url = config.get(f"{tier}_think_backend_url") or config.get("backend_url")
    else:
        base_url = config.get(f"{tier}_think_backend_url")

    kwargs = build_llm_kwargs({**config, "llm_provider": provider}, provider=provider)
    return create_llm_client(
        provider=provider,
        model=config[f"{tier}_think_llm"],
        base_url=base_url,
        **kwargs,
        **extra,
    )


def require_provider_api_key(provider: str) -> str:
    """Return the API key for a provider, raising if not configured."""
    return require_api_key(provider)