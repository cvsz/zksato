"""Local LLM client for offline/private inference.

Supports local LLM backends that expose an OpenAI-compatible API:
- Ollama (http://localhost:11434/v1/chat/completions)
- llama.cpp server (http://localhost:8080/v1/chat/completions)
- vLLM (http://localhost:8000/v1/chat/completions)
- Text Generation Inference (TGI) (http://localhost:8080/v1/chat/completions)

All financial data stays on-premise — no API calls to external services.
Designed for zksato's paper/sandbox trading environments where broker
credentials and market data must never leave the local network.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LocalLLMBackend(StrEnum):
    """Supported local LLM backends.

    All backends expose an OpenAI-compatible /v1/chat/completions endpoint.
    """

    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    VLLM = "vllm"
    TGI = "tgi"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass
class LocalLLMConfig:
    """Configuration for local LLM client."""

    backend: LocalLLMBackend = LocalLLMBackend.OLLAMA
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    api_key: str | None = None  # Optional; some backends require auth
    temperature: float = 0.7
    max_input_tokens: int = 4096
    max_output_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    timeout_seconds: float = 60.0

    @property
    def chat_endpoint(self) -> str:
        """Get the chat completions endpoint URL."""
        return f"{self.base_url.rstrip('/')}/v1/chat/completions"

    @property
    def models_endpoint(self) -> str:
        """Get the models list endpoint URL."""
        return f"{self.base_url.rstrip('/')}/v1/models"


@dataclass
class LocalLLMResponse:
    """Structured LLM response from a local backend."""

    content: str
    model: str
    backend: LocalLLMBackend
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    finish_reason: str
    safety_ratings: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class LocalLLMClient:
    """Local LLM client for offline/private inference.

    Connects to locally-hosted LLM backends (Ollama, llama.cpp, vLLM, TGI)
    via their OpenAI-compatible API. No data leaves the local machine —
    critical for zksato's paper/sandbox trading environments where broker
    credentials, PINs, and market data must remain server-side.

    Safety invariants preserved:
    - No external network calls beyond the configured local backend
    - API keys (if any) stay server-side, never logged or rendered
    - Fail-closed: stub mode when backend is unreachable
    - Deterministic: same model, same parameters, same output (when
      temperature=0 and backend is deterministic)
    """

    def __init__(self, config: LocalLLMConfig | None = None) -> None:
        self.config = config or LocalLLMConfig()
        self._http_client: Any = None
        self._initialized = False
        self._backend_available: bool | None = None

    async def initialize(self) -> None:
        """Initialize the HTTP client and check backend availability."""
        if self._initialized:
            return
        try:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers={
                    "Content-Type": "application/json",
                },
            )
            if self.config.api_key:
                self._http_client.headers["Authorization"] = f"Bearer {self.config.api_key}"
        except ImportError:
            logger.warning("httpx not installed; client will operate in stub mode")
        self._initialized = True
        # Probe backend availability (non-fatal if unreachable)
        await self._probe_backend()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
        self._initialized = False

    async def _probe_backend(self) -> None:
        """Probe the backend to check availability and list models.

        Non-fatal — sets _backend_available flag for callers to inspect.
        """
        if not self._http_client:
            self._backend_available = False
            return
        try:
            resp = await self._http_client.get(self.config.models_endpoint)
            self._backend_available = resp.is_success
            if self._backend_available:
                logger.info(
                    "Local LLM backend available at %s",
                    self.config.base_url,
                )
            else:
                logger.warning(
                    "Local LLM backend returned status %s at %s",
                    resp.status_code,
                    self.config.base_url,
                )
        except Exception as exc:
            logger.debug(
                "Local LLM backend probe failed: %s",
                exc,
            )
            self._backend_available = False

    @property
    def is_available(self) -> bool:
        """Return True if the backend was reachable at initialization."""
        return self._backend_available is True

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,  # noqa: ANN401
    ) -> dict[str, Any]:
        """Build the OpenAI-compatible chat completions request payload."""
        return {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "stream": False,
            **kwargs,
        }

    def _parse_response(self, raw: dict[str, Any]) -> LocalLLMResponse:
        """Parse the OpenAI-compatible chat completions response."""
        choices = raw.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            finish_reason = choices[0].get("finish_reason", "stop")
        else:
            content = raw.get("content", "")
            finish_reason = raw.get("finish_reason", "stop")

        usage = raw.get("usage", {})
        return LocalLLMResponse(
            content=content,
            model=raw.get("model", self.config.model),
            backend=self.config.backend,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_seconds=raw.get("latency_seconds", 0.0),
            finish_reason=finish_reason,
            metadata=raw.get("metadata", {}),
        )

    async def generate(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,  # noqa: ANN401
    ) -> LocalLLMResponse:
        """Generate a response using the local LLM backend.

        Args:
            messages: Chat messages in OpenAI-compatible format.
            **kwargs: Additional provider-specific parameters (e.g.,
                temperature, max_tokens override).

        Returns:
            Structured LocalLLMResponse with content, token counts,
            and metadata.

        Raises:
            RuntimeError: If the client is not initialized.
            ConnectionError: If the backend is unreachable.
        """
        if not self._initialized:
            await self.initialize()

        payload = self._build_payload(messages, **kwargs)
        start = datetime.now(UTC)
        last_error: Exception | None = None
        response: LocalLLMResponse | None = None

        for attempt in range(self.config.max_retries):
            try:
                resp = await self._http_client.post(
                    self.config.chat_endpoint,
                    json=payload,
                )
                resp.raise_for_status()
                raw = resp.json()
                latency = (datetime.now(UTC) - start).total_seconds()
                response = self._parse_response(raw)
                response.latency_seconds = latency
                break
            except httpx.ConnectError as exc:
                last_error = exc
                logger.warning(
                    "Local LLM backend unreachable at %s (attempt %d/%d)",
                    self.config.base_url,
                    attempt + 1,
                    self.config.max_retries,
                )
                if attempt < self.config.max_retries - 1:
                    delay = min(
                        self.config.base_delay_seconds * (2**attempt),
                        self.config.max_delay_seconds,
                    )
                    await asyncio.sleep(delay)
            except Exception as exc:
                last_error = exc
                if attempt < self.config.max_retries - 1:
                    delay = min(
                        self.config.base_delay_seconds * (2**attempt),
                        self.config.max_delay_seconds,
                    )
                    await asyncio.sleep(delay)

        if response is None:
            raise ConnectionError(
                f"Local LLM backend at {self.config.base_url} is unreachable "
                f"after {self.config.max_retries} attempts: {last_error}"
            )
        return response

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        temperature: float | None = None,
    ) -> LocalLLMResponse:
        """Generate code using the local LLM backend.

        Optimized for coding tasks — produces clean, production-ready code
        without rewriting unrelated files.
        """
        temp = temperature if temperature is not None else self.config.temperature
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert software engineer. Write clean, "
                    f"production-ready {language} code. Focus on surgical edits "
                    "without rewriting unrelated files. Include type hints, "
                    "docstrings, and error handling."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        # Override temperature for this call
        old_temp = self.config.temperature
        self.config.temperature = temp
        try:
            return await self.generate(messages)
        finally:
            self.config.temperature = old_temp

    async def analyze_code(
        self,
        code: str,
        language: str = "python",
    ) -> LocalLLMResponse:
        """Analyze code for bugs, security issues, and improvements.

        Suitable for reviewing trading strategy code, risk engine logic,
        and broker adapter implementations.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a senior code reviewer. Analyze the provided "
                    f"{language} code for bugs, security vulnerabilities, "
                    "performance issues, and maintainability concerns. "
                    "Provide specific, actionable recommendations."
                ),
            },
            {"role": "user", "content": f"Code to analyze:\n\n```{language}\n{code}\n```"},
        ]
        return await self.generate(messages)

    async def verify_test(
        self,
        test_code: str,
        source_code: str,
    ) -> LocalLLMResponse:
        """Verify that tests adequately cover the source code.

        Returns pass/fail assessment with gap analysis.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a test verification engineer. Compare the test code "
                    "against the source code and determine if the tests adequately "
                    "cover all branches, edge cases, and error conditions. "
                    "Report pass/fail with specific gap analysis."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source code:\n```python\n{source_code}\n```\n\n"
                    f"Test code:\n```python\n{test_code}\n```"
                ),
            },
        ]
        return await self.generate(messages)

    def get_info(self) -> dict[str, Any]:
        """Get client information and capabilities."""
        return {
            "model": self.config.model,
            "backend": self.config.backend.value,
            "provider": "local",
            "base_url": self.config.base_url,
            "capabilities": [
                "code_generation",
                "code_analysis",
                "test_verification",
                "agentic_workflows",
                "offline_inference",
            ],
            "initialized": self._initialized,
            "backend_available": self._backend_available,
            "max_input_tokens": self.config.max_input_tokens,
            "max_output_tokens": self.config.max_output_tokens,
        }
