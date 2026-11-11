"""LLM client abstractions for multi-provider LLM support.

Provides a unified interface for creating LLM clients across multiple
providers (OpenAI, Anthropic, Google, Azure, Bedrock, OpenAI-compatible).
All clients are used for advisory/research purposes only — they never
bypass RiskEngine or TradingService.
"""

from __future__ import annotations

from zksato.llm_clients.api_key_env import (
    detect_api_key_env,
    get_api_key,
    mask_api_key,
    require_api_key,
)
from zksato.llm_clients.base_client import BaseLLMClient, normalize_content
from zksato.llm_clients.capabilities import ProviderCapabilities, get_capabilities
from zksato.llm_clients.factory import (
    build_llm_kwargs,
    create_llm_client,
    create_tier_client,
    require_provider_api_key,
    tier_provider,
)
from zksato.llm_clients.model_catalog import DEFAULT_CATALOG, ModelCatalog
from zksato.llm_clients.validators import suggest_models, validate_model

__all__ = [
    "BaseLLMClient",
    "normalize_content",
    "ProviderCapabilities",
    "get_capabilities",
    "ModelCatalog",
    "DEFAULT_CATALOG",
    "create_llm_client",
    "create_tier_client",
    "build_llm_kwargs",
    "tier_provider",
    "validate_model",
    "suggest_models",
    "require_api_key",
    "get_api_key",
    "detect_api_key_env",
    "mask_api_key",
    "require_provider_api_key",
]
