from __future__ import annotations

from typing import Any

from zksato.llm_clients.api_key_env import require_api_key
from zksato.llm_clients.base_client import BaseLLMClient


def is_openai_compatible(provider: str) -> bool:
    """Return True if the provider routes through the OpenAI-compatible client."""
    return provider in {
        "openai",
        "chatgpt",
        "azure",
        "openrouter",
        "groq",
        "deepseek",
        "kimi",
        "minimax",
        "ollama",
        "mistral",
        "cohere",
        "huggingface",
        "together",
        "perplexity",
        "cerebras",
        "fireworks",
        "nvidia",
        "sambanova",
    }


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible LLM client.

    Routes through LangChain's ChatOpenAI (or the provider's OpenAI-compatible
    endpoint when ``provider`` is set). Supports OpenAI, Azure OpenAI, and any
    OpenAI-compatible endpoint (OpenRouter, Groq, Together, etc.).
    """

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        provider: str = "openai",
        **kwargs: Any,
    ) -> None:
        super().__init__(model, base_url, **kwargs)
        self.provider = provider
        self._llm: Any = None

    def _build_client(self) -> Any:
        from langchain_openai import ChatOpenAI

        api_key = require_api_key(self.provider)
        client_kwargs: dict[str, Any] = {
            "model": self.model,
            "api_key": api_key,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        # Forward provider-specific kwargs
        for key in ("temperature", "max_retries", "max_tokens", "reasoning_effort"):
            if key in self.kwargs and self.kwargs[key] is not None:
                client_kwargs[key] = self.kwargs[key]

        return ChatOpenAI(**client_kwargs)

    def get_llm(self) -> Any:
        if self._llm is None:
            self._llm = self._build_client()
            self.warn_if_unknown_model()
        return self._llm

    def validate_model(self) -> bool:
        from zksato.llm_clients.validators import validate_model

        return validate_model(self.provider, self.model)


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, base_url, **kwargs)
        self.provider = "anthropic"
        self._llm: Any = None

    def _build_client(self) -> Any:
        from langchain_anthropic import ChatAnthropic

        api_key = require_api_key(self.provider)
        client_kwargs: dict[str, Any] = {
            "model": self.model,
            "anthropic_api_key": api_key,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        # Forward provider-specific kwargs
        for key in ("temperature", "max_retries", "max_tokens", "effort"):
            if key in self.kwargs and self.kwargs[key] is not None:
                client_kwargs[key] = self.kwargs[key]

        return ChatAnthropic(**client_kwargs)

    def get_llm(self) -> Any:
        if self._llm is None:
            self._llm = self._build_client()
            self.warn_if_unknown_model()
        return self._llm

    def validate_model(self) -> bool:
        from zksato.llm_clients.validators import validate_model

        return validate_model(self.provider, self.model)


class GoogleClient(BaseLLMClient):
    """Google Gemini client."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, base_url, **kwargs)
        self.provider = "google"
        self._llm: Any = None

    def _build_client(self) -> Any:
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = require_api_key(self.provider)
        client_kwargs: dict[str, Any] = {
            "model": self.model,
            "google_api_key": api_key,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        # Forward provider-specific kwargs
        for key in ("temperature", "max_retries", "max_output_tokens", "thinking_level"):
            if key in self.kwargs and self.kwargs[key] is not None:
                client_kwargs[key] = self.kwargs[key]

        return ChatGoogleGenerativeAI(**client_kwargs)

    def get_llm(self) -> Any:
        if self._llm is None:
            self._llm = self._build_client()
            self.warn_if_unknown_model()
        return self._llm

    def validate_model(self) -> bool:
        from zksato.llm_clients.validators import validate_model

        return validate_model(self.provider, self.model)


class AzureOpenAIClient(BaseLLMClient):
    """Azure OpenAI client."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, base_url, **kwargs)
        self.provider = "azure"
        self._llm: Any = None

    def _build_client(self) -> Any:
        from langchain_openai import AzureChatOpenAI

        api_key = require_api_key(self.provider)
        client_kwargs: dict[str, Any] = {
            "model": self.model,
            "api_key": api_key,
        }
        if self.base_url:
            client_kwargs["azure_endpoint"] = self.base_url
        else:
            client_kwargs["azure_endpoint"] = "https://openai.azure.com"

        # Forward provider-specific kwargs
        for key in ("temperature", "max_retries", "max_tokens", "reasoning_effort"):
            if key in self.kwargs and self.kwargs[key] is not None:
                client_kwargs[key] = self.kwargs[key]

        return AzureChatOpenAI(**client_kwargs)

    def get_llm(self) -> Any:
        if self._llm is None:
            self._llm = self._build_client()
            self.warn_if_unknown_model()
        return self._llm

    def validate_model(self) -> bool:
        from zksato.llm_clients.validators import validate_model

        return validate_model(self.provider, self.model)


class BedrockClient(BaseLLMClient):
    """AWS Bedrock client."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, base_url, **kwargs)
        self.provider = "bedrock"
        self._llm: Any = None

    def _build_client(self) -> Any:
        from langchain_aws import ChatBedrock

        client_kwargs: dict[str, Any] = {
            "model": self.model,
        }
        if self.base_url:
            client_kwargs["endpoint_url"] = self.base_url

        # Forward provider-specific kwargs
        for key in ("temperature", "max_retries"):
            if key in self.kwargs and self.kwargs[key] is not None:
                client_kwargs[key] = self.kwargs[key]

        return ChatBedrock(**client_kwargs)

    def get_llm(self) -> Any:
        if self._llm is None:
            self._llm = self._build_client()
            self.warn_if_unknown_model()
        return self._llm

    def validate_model(self) -> bool:
        from zksato.llm_clients.validators import validate_model

        return validate_model(self.provider, self.model)
