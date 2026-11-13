"""Multi-provider model routing for autonomous agent orchestration."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol

from zksato_api.llm_clients import (  # type: ignore[import-untyped]
    LocalLLMBackend,
    LocalLLMClient,
    LocalLLMConfig,
    LocalLLMError,
    LocalLLMResponse,
)

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM providers."""

    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    VLLM = "vllm"
    TGI = "tgi"


class ModelCapability(str, Enum):
    """Model capabilities."""

    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    TEST_VERIFICATION = "test_verification"
    REASONING = "reasoning"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALLING = "tool_calling"
    STREAMING = "streaming"
    LARGE_CONTEXT = "large_context"


@dataclass
class ModelMetadata:
    """Metadata about a model."""

    model_id: str
    provider: ProviderType
    display_name: str
    capabilities: set[ModelCapability]
    context_window: int
    max_output_tokens: int
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    is_free: bool = False
    supports_thinking: bool = False
    thinking_levels: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class ProviderHealth:
    """Provider health status."""

    provider: ProviderType
    is_healthy: bool
    latency_ms: float = 0.0
    error_rate: float = 0.0
    rate_limit_remaining: int | None = None
    rate_limit_reset: datetime | None = None
    quota_remaining: float | None = None  # For paid providers
    quota_reset: datetime | None = None
    last_check: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_error: str | None = None
    models_available: list[str] = field(default_factory=list)
    consecutive_failures: int = 0
    circuit_breaker_open: bool = False
    circuit_breaker_opened_at: datetime | None = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0


@dataclass
class UsageRecord:
    """Record of model usage for cost/quota tracking."""

    model_id: str
    provider: ProviderType
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None = None
    task_id: str | None = None


@dataclass
class UsageTracker:
    """Tracks usage and costs across models and providers."""

    records: list[UsageRecord] = field(default_factory=list)
    per_model_cost: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    per_model_tokens: dict[str, tuple[int, int]] = field(
        default_factory=lambda: defaultdict(lambda: (0, 0))
    )
    per_provider_cost: dict[ProviderType, float] = field(default_factory=lambda: defaultdict(float))
    per_session_cost: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    # Ensure defaultdict is available in lambda scope
    _defaultdict = defaultdict
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def record(self, record: UsageRecord) -> None:
        """Record a usage event."""
        self.records.append(record)
        self.per_model_cost[record.model_id] += record.cost
        input_t, output_t = self.per_model_tokens[record.model_id]
        self.per_model_tokens[record.model_id] = (
            input_t + record.input_tokens,
            output_t + record.output_tokens,
        )
        self.per_provider_cost[record.provider] += record.cost
        if record.session_id:
            self.per_session_cost[record.session_id] += record.cost
        self.total_cost += record.cost
        self.total_input_tokens += record.input_tokens
        self.total_output_tokens += record.output_tokens

    def get_model_usage(self, model_id: str) -> dict[str, Any]:
        """Get usage stats for a model."""
        input_t, output_t = self.per_model_tokens.get(model_id, (0, 0))
        return {
            "model_id": model_id,
            "total_cost": self.per_model_cost.get(model_id, 0.0),
            "input_tokens": input_t,
            "output_tokens": output_t,
            "total_tokens": input_t + output_t,
        }

    def get_provider_usage(self, provider: ProviderType) -> dict[str, Any]:
        """Get usage stats for a provider."""
        return {
            "provider": provider.value,
            "total_cost": self.per_provider_cost.get(provider, 0.0),
        }

    def get_session_usage(self, session_id: str) -> dict[str, Any]:
        """Get usage stats for a session."""
        return {
            "session_id": session_id,
            "total_cost": self.per_session_cost.get(session_id, 0.0),
        }

    def get_total_usage(self) -> dict[str, Any]:
        """Get overall usage stats."""
        return {
            "total_cost": self.total_cost,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "models_used": len(self.per_model_cost),
        }


@dataclass
class RoutingContext:
    """Context for routing decisions."""

    task_type: str
    required_capabilities: set[ModelCapability]
    min_context_window: int = 4096
    prefer_free: bool = True
    max_cost_per_request: float | None = None
    thinking_level: str | None = None
    prefer_local: bool = False
    session_id: str | None = None
    usage_tracker: UsageTracker | None = None


@dataclass
class RoutingDecision:
    """Model routing decision."""

    model_id: str
    provider: ProviderType
    reasoning: str
    confidence: float
    fallback_chain: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_latency_ms: int = 0


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> LocalLLMResponse:
        """Generate a response."""
        ...

    async def health_check(self) -> ProviderHealth:
        """Check provider health."""
        ...

    def get_models(self) -> list[ModelMetadata]:
        """Get available models."""
        ...


class LocalProvider:
    """Local LLM provider (Ollama, llama.cpp, vLLM, TGI)."""

    def __init__(self, config: LocalLLMConfig) -> None:
        self.config = config
        self.client = LocalLLMClient(config=config)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the client."""
        if not self._initialized:
            await self.client.initialize()
            self._initialized = True

    async def generate(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> LocalLLMResponse:
        """Generate a response."""
        if not self._initialized:
            await self.initialize()
        return await self.client.generate(messages, **kwargs)

    async def generate_with_tracking(
        self,
        messages: list[dict[str, str]],
        health: ProviderHealth,
        **kwargs: Any,
    ) -> LocalLLMResponse:
        """Generate a response with health tracking."""
        if not self._initialized:
            await self.initialize()
        try:
            response = await self.client.generate(messages, **kwargs)
            # Record success
            health.consecutive_failures = 0
            health.successful_requests += 1
            health.total_requests += 1
            return response
        except Exception:
            # Record failure
            health.consecutive_failures += 1
            health.failed_requests += 1
            health.total_requests += 1
            # Open circuit breaker after 5 consecutive failures
            if health.consecutive_failures >= 5 and not health.circuit_breaker_open:
                health.circuit_breaker_open = True
                health.circuit_breaker_opened_at = datetime.now(UTC)
            raise

    async def health_check(self) -> ProviderHealth:
        """Check provider health."""
        start = time.time()
        try:
            if not self._initialized:
                await self.initialize()
            # Probe models endpoint
            await self.client._probe_backend()
            latency_ms = (time.time() - start) * 1000
            return ProviderHealth(
                provider=self._get_provider_type(),
                is_healthy=self.client.is_available,
                latency_ms=latency_ms,
                models_available=[self.config.model] if self.client.is_available else [],
            )
        except Exception as exc:
            latency_ms = (time.time() - start) * 1000
            return ProviderHealth(
                provider=self._get_provider_type(),
                is_healthy=False,
                latency_ms=latency_ms,
                last_error=str(exc),
            )

    def get_models(self) -> list[ModelMetadata]:
        """Get available models."""
        return [
            ModelMetadata(
                model_id=self.config.model,
                provider=self._get_provider_type(),
                display_name=f"{self.config.backend.value}:{self.config.model}",
                capabilities={
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_ANALYSIS,
                    ModelCapability.TEST_VERIFICATION,
                    ModelCapability.REASONING,
                },
                context_window=self.config.max_input_tokens,
                max_output_tokens=self.config.max_output_tokens,
                is_free=True,
                supports_thinking=True,
                thinking_levels=["low", "medium", "high", "xhigh"],
                description=f"Local {self.config.backend.value} model",
            )
        ]

    def _get_provider_type(self) -> ProviderType:
        """Map backend to provider type."""
        mapping = {
            LocalLLMBackend.OLLAMA: ProviderType.OLLAMA,
            LocalLLMBackend.LLAMACPP: ProviderType.LLAMACPP,
            LocalLLMBackend.VLLM: ProviderType.VLLM,
            LocalLLMBackend.TGI: ProviderType.TGI,
            LocalLLMBackend.OPENAI_COMPATIBLE: ProviderType.LOCAL,
        }
        return mapping.get(self.config.backend, ProviderType.LOCAL)


class ProviderRegistry:
    """Registry for LLM providers."""

    def __init__(self) -> None:
        self._providers: dict[ProviderType, LLMProvider] = {}
        self._model_metadata: dict[str, ModelMetadata] = {}
        self._health: dict[ProviderType, ProviderHealth] = {}

    def register(self, provider: LLMProvider, provider_type: ProviderType) -> None:
        """Register a provider."""
        self._providers[provider_type] = provider
        # Register models
        for model in provider.get_models():
            self._model_metadata[model.model_id] = model

    def unregister(self, provider_type: ProviderType) -> bool:
        """Unregister a provider."""
        if provider_type in self._providers:
            provider = self._providers.pop(provider_type)
            for model in provider.get_models():
                self._model_metadata.pop(model.model_id, None)
            self._health.pop(provider_type, None)
            return True
        return False

    def get_provider(self, provider_type: ProviderType) -> LLMProvider | None:
        """Get a provider by type."""
        return self._providers.get(provider_type)

    def get_model(self, model_id: str) -> ModelMetadata | None:
        """Get model metadata."""
        return self._model_metadata.get(model_id)

    def list_models(self) -> list[ModelMetadata]:
        """List all registered models."""
        return list(self._model_metadata.values())

    def list_providers(self) -> list[ProviderType]:
        """List all registered provider types."""
        return list(self._providers.keys())

    async def check_health(
        self, provider_type: ProviderType | None = None
    ) -> dict[ProviderType, ProviderHealth]:
        """Check health of providers."""
        providers_to_check = [provider_type] if provider_type else list(self._providers.keys())

        for ptype in providers_to_check:
            provider = self._providers.get(ptype)
            if provider:
                self._health[ptype] = await provider.health_check()

        return self._health

    def get_health(self, provider_type: ProviderType) -> ProviderHealth | None:
        """Get cached health for a provider."""
        return self._health.get(provider_type)

    def record_success(self, provider_type: ProviderType) -> None:
        """Record a successful request."""
        health = self._health.get(provider_type)
        if health:
            health.consecutive_failures = 0
            health.successful_requests += 1
            health.total_requests += 1

    def record_failure(self, provider_type: ProviderType) -> None:
        """Record a failed request."""
        health = self._health.get(provider_type)
        if health:
            health.consecutive_failures += 1
            health.failed_requests += 1
            health.total_requests += 1
            # Open circuit breaker after 5 consecutive failures
            if health.consecutive_failures >= 5 and not health.circuit_breaker_open:
                health.circuit_breaker_open = True
                health.circuit_breaker_opened_at = datetime.now(UTC)


class ModelRouter:
    """Intelligent model router with fallback chain."""

    def __init__(
        self,
        registry: ProviderRegistry,
        default_context: RoutingContext | None = None,
    ) -> None:
        self.registry = registry
        self.default_context = default_context or RoutingContext(
            task_type="general",
            required_capabilities={ModelCapability.TEXT_GENERATION},
        )
        self.usage_tracker = UsageTracker()

    def route(self, context: RoutingContext | None = None) -> RoutingDecision:
        """Route to the best model based on context."""
        ctx = context or self.default_context

        # Get healthy providers (respecting circuit breakers)
        healthy_providers = {}
        for ptype, health in self.registry._health.items():
            if health.is_healthy and not health.circuit_breaker_open:
                healthy_providers[ptype] = health
                # Check if circuit breaker should reset (after 60 seconds)
            elif health.circuit_breaker_open and health.circuit_breaker_opened_at:
                elapsed = (datetime.now(UTC) - health.circuit_breaker_opened_at).total_seconds()
                if elapsed > 60:  # Reset after 60 seconds
                    health.circuit_breaker_open = False
                    health.consecutive_failures = 0
                    healthy_providers[ptype] = health
        if not healthy_providers:
            # Try all providers (including those with open circuit breakers)
            healthy_providers = {
                ptype: h for ptype, h in self.registry._health.items() if h.is_healthy
            }

        if not healthy_providers:
            # Try all providers
            healthy_providers = self.registry._health

        # Find candidate models
        candidates: list[tuple[ModelMetadata, ProviderHealth, float]] = []

        for model in self.registry._model_metadata.values():
            health = healthy_providers.get(model.provider)
            if not health or not health.is_healthy:
                continue

            # Check capabilities
            if not ctx.required_capabilities.issubset(model.capabilities):
                continue

            # Check context window
            if model.context_window < ctx.min_context_window:
                continue

            # Check cost
            if ctx.max_cost_per_request is not None:
                estimated_cost = (
                    model.cost_per_1k_input * 10 + model.cost_per_1k_output * 5
                ) / 1000  # Rough estimate
                if estimated_cost > ctx.max_cost_per_request:
                    continue

            # Check quota/rate limits
            if health.rate_limit_remaining is not None and health.rate_limit_remaining <= 0:
                continue
            if health.quota_remaining is not None and health.quota_remaining <= 0:
                continue

            # Score the model
            score = self._score_model(model, health, ctx)
            candidates.append((model, health, score))

        if not candidates:
            raise ValueError("No suitable model found for the given context")

        # Sort by score (highest first)
        candidates.sort(key=lambda x: x[2], reverse=True)

        best_model, best_health, best_score = candidates[0]

        # Build fallback chain (filter out models with circuit breakers or quota issues)
        fallback_chain = [
            m.model_id
            for m, h, s in candidates[1:6]
            if not h.circuit_breaker_open
            and (h.rate_limit_remaining is None or h.rate_limit_remaining > 0)
            and (h.quota_remaining is None or h.quota_remaining > 0)
        ]

        return RoutingDecision(
            model_id=best_model.model_id,
            provider=best_model.provider,
            reasoning=f"Selected {best_model.display_name} (score: {best_score:.2f})",
            confidence=min(best_score, 1.0),
            fallback_chain=fallback_chain,
            estimated_cost=self._estimate_cost(best_model),
            estimated_latency_ms=int(best_health.latency_ms),
        )

    def _score_model(
        self,
        model: ModelMetadata,
        health: ProviderHealth,
        ctx: RoutingContext,
    ) -> float:
        """Score a model for the given context."""
        score = 0.0

        # Prefer free models
        if ctx.prefer_free and model.is_free:
            score += 0.4

        # Prefer local models
        if ctx.prefer_local and model.provider in (
            ProviderType.LOCAL,
            ProviderType.OLLAMA,
            ProviderType.LLAMACPP,
            ProviderType.VLLM,
            ProviderType.TGI,
        ):
            score += 0.3

        # Health score (lower latency = higher score)
        if health.latency_ms > 0:
            latency_score = max(0, 1 - (health.latency_ms / 10000))  # Normalize
            score += latency_score * 0.2

        # Capability match bonus
        capability_match = len(ctx.required_capabilities & model.capabilities)
        score += capability_match * 0.1

        # Context window adequacy
        if model.context_window >= ctx.min_context_window * 2:
            score += 0.1

        # Thinking level support
        if ctx.thinking_level and ctx.thinking_level in model.thinking_levels:
            score += 0.1

        return score

    def _estimate_cost(self, model: ModelMetadata) -> float:
        """Estimate cost per request."""
        # Rough estimate: 10k input tokens, 5k output tokens
        return (model.cost_per_1k_input * 10 + model.cost_per_1k_output * 5) / 1000


class ModelRouterWithFallback:
    """Model router with automatic fallback."""

    def __init__(self, router: ModelRouter, max_fallbacks: int = 3) -> None:
        self.router = router
        self.max_fallbacks = max_fallbacks
        self._fallback_attempts: dict[str, int] = {}

    async def execute_with_fallback(
        self,
        messages: list[dict[str, str]],
        context: RoutingContext | None = None,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> tuple[LocalLLMResponse, RoutingDecision]:
        """Execute with automatic fallback on failure."""
        decision = self.router.route(context)
        last_error: Exception | None = None

        for attempt in range(self.max_fallbacks + 1):
            model_id = decision.model_id if attempt == 0 else decision.fallback_chain[attempt - 1]

            if not model_id:
                break

            model_meta = self.router.registry.get_model(model_id)
            if not model_meta:
                continue

            provider = self.router.registry.get_provider(model_meta.provider)

            if not provider:
                continue

            try:
                self._fallback_attempts[model_id] = self._fallback_attempts.get(model_id, 0) + 1
                # Use the new tracking method
                if hasattr(provider, "generate_with_tracking"):
                    health = self.router.registry._health.get(model_meta.provider)
                    response = await provider.generate_with_tracking(messages, health, **kwargs)
                else:
                    response = await provider.generate(messages, **kwargs)

                if attempt > 0:
                    logger.info("Fallback succeeded on attempt %d with model %s", attempt, model_id)

                # Record success
                self.router.registry.record_success(model_meta.provider)

                # Track usage
                if context and context.usage_tracker:
                    cost = (
                        model_meta.cost_per_1k_input * response.input_tokens
                        + model_meta.cost_per_1k_output * response.output_tokens
                    ) / 1000
                    context.usage_tracker.record(
                        UsageRecord(
                            model_id=model_id,
                            provider=model_meta.provider,
                            input_tokens=response.input_tokens,
                            output_tokens=response.output_tokens,
                            cost=cost,
                            session_id=session_id,
                        )
                    )

                return response, decision

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Model %s failed on attempt %d: %s",
                    model_id,
                    attempt + 1,
                    exc,
                )

                # Record failure
                self.router.registry.record_failure(model_meta.provider)

                # Check health and potentially update
                await self.router.registry.check_health(model_meta.provider)

                # If not last attempt, try next fallback
                if attempt < self.max_fallbacks:
                    continue

        # All fallbacks exhausted
        raise LocalLLMError(
            f"All models failed after {self.max_fallbacks + 1} attempts. Last error: {last_error}",
            error_code="ALL_MODELS_FAILED",
        ) from last_error
