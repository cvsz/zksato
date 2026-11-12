from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


def normalize_content(response: Any) -> Any:
    """Normalize LLM response content to a plain string.

    Multiple providers (OpenAI Responses API, Google Gemini 3) return content
    as a list of typed blocks, e.g. [{'type': 'reasoning', ...}, {'type': 'text', 'text': '...'}].
    Downstream agents expect response.content to be a string. This extracts
    and joins the text blocks, discarding reasoning/metadata blocks.
    """
    content = response.content
    if isinstance(content, list):
        texts = [
            item.get("text", "")
            if isinstance(item, dict) and item.get("type") == "text"
            else item
            if isinstance(item, str)
            else ""
            for item in content
        ]
        response.content = "\n".join(t for t in texts if t)
    return response


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients.

    All provider clients must implement ``get_llm`` (returning a LangChain-compatible
    chat model) and ``validate_model`` (checking the model against the provider's
    known list).
    """

    def __init__(self, model: str, base_url: str | None = None, **kwargs: Any) -> None:
        self.model = model
        self.base_url = base_url
        self.kwargs = kwargs
        self.provider: str = self.__class__.__name__.removesuffix("Client").lower()

    def get_provider_name(self) -> str:
        """Return the provider name used in warning messages."""
        return str(self.provider)

    def warn_if_unknown_model(self) -> None:
        """Warn when the model is outside the known list for the provider."""
        if self.validate_model():
            return
        warnings.warn(
            (
                f"Model '{self.model}' is not in the known model list for "
                f"provider '{self.get_provider_name()}'. Continuing anyway."
            ),
            RuntimeWarning,
            stacklevel=2,
        )

    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """Return the configured LangChain-compatible LLM instance."""
        ...

    @abstractmethod
    def validate_model(self) -> bool:
        """Validate that the model is supported by this client."""
        ...
