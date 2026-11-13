"""Local LLM client for offline/private inference.

Supports local LLM backends that expose an OpenAI-compatible API:
- Ollama (http://localhost:11434/v1/chat/completions)
- llama.cpp server (http://localhost:8080/v1/chat/completions)
- vLLM (http://localhost:8000/v1/chat/completions)
- Text Generation Inference (TGI) (http://localhost:8080/v1/chat/completions)

All financial data stays on-premise — no API calls to external services.
Designed for zksato's paper/sandbox trading environments where broker
credentials and market data must never leave the local network.

Patterns adapted from gemini-cli's LocalLiteRtLmClient:
- Short timeout for local server (should respond quickly)
- Dummy API key for local servers (not used for authentication)
- AbortSignal support for cancellation
- JSON response mode for structured output
- Detailed error classification for local server failures
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, cast

import httpx

HTTP_STATUS_SERVER_ERROR = 500

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


class LocalLLMError(Exception):
    """Base exception for local LLM errors."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class LocalLLMConnectionError(LocalLLMError):
    """Raised when the local LLM backend cannot be reached."""


class LocalLLMModelError(LocalLLMError):
    """Raised when the model is unsupported or not downloaded."""


class LocalLLMContextError(LocalLLMError):
    """Raised when the model's context window is exceeded."""


@dataclass
class LocalLLMConfig:
    """Configuration for local LLM client."""

    backend: LocalLLMBackend = LocalLLMBackend.OLLAMA
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    api_key: str | None = None  # Optional; local servers typically don't need auth
    temperature: float = 0.7
    max_input_tokens: int = 4096
    max_output_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    # Short timeout for local server — should respond quickly.
    # If the server is not started, connection is refused immediately.
    # For llama.cpp on CPU, generation can take 30-60+ seconds for complex tasks.
    timeout_seconds: float = 60.0
    # JSON mode for structured output.
    json_mode: bool = False

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
        self._http_client: httpx.AsyncClient | None = None
        self._initialized = False
        self._backend_available: bool | None = None
        self._stub_mode = False

    async def initialize(self) -> None:
        """Initialize the HTTP client and check backend availability."""
        if self._initialized:
            return
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            headers={
                "Content-Type": "application/json",
            },
        )
        # Local LLM servers typically don't require an API key, but if one is
        # configured it is sent as a Bearer token. This dummy value is not used
        # for authentication by local servers (mirrors gemini-cli pattern).
        if self.config.api_key:
            self._http_client.headers["Authorization"] = f"Bearer {self.config.api_key}"
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
            self._stub_mode = True
            return
        try:
            resp = await self._http_client.get(self.config.models_endpoint)
            self._backend_available = resp.is_success
            self._stub_mode = not resp.is_success
            if self._backend_available:
                logger.info(
                    "Local LLM backend available at %s",
                    self.config.base_url,
                )
            else:
                logger.warning(
                    "Local LLM backend returned status %s at %s; falling back to stub mode",
                    resp.status_code,
                    self.config.base_url,
                )
        except Exception as exc:
            logger.debug(
                "Local LLM backend probe failed: %s; falling back to stub mode",
                exc,
            )
            self._backend_available = False
            self._stub_mode = True

    def _generate_stub_response(self, messages: list[dict[str, str]]) -> LocalLLMResponse:
        """Generate a stub response when the backend is unavailable."""
        # Get the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # Simple stub response based on the message content
        content = (
            f"[Local LLM Stub Mode] Backend unavailable. "
            f"Your message: {user_message[:100]}...\n\n"
            f"Configure a local LLM backend (Ollama, llama.cpp, vLLM, or TGI) "
            f"at {self.config.base_url} to enable real inference."
        )

        return LocalLLMResponse(
            content=content,
            model=self.config.model,
            backend=self.config.backend,
            input_tokens=0,
            output_tokens=0,
            latency_seconds=0.0,
            finish_reason="stub",
            metadata={"stub": True},
        )

    @property
    def is_available(self) -> bool:
        """Return True if the backend was reachable at initialization."""
        return self._backend_available is True

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build the OpenAI-compatible chat completions request payload."""
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_output_tokens,
            "top_p": self.config.top_p,
            "top_k": self.config.top_k,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "stream": False,
        }
        if self.config.json_mode:
            payload["response_format"] = {"type": "json_object"}
        payload.update(kwargs)
        return payload

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

    @staticmethod
    def _classify_error(
        error: Exception,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> LocalLLMError:
        """Classify local LLM errors for appropriate handling.

        Mirrors gemini-cli's error classification:
        - Connection errors → LocalLLMConnectionError
        - 4xx client errors → LocalLLMModelError (unsupported model, etc.)
        - Context window exceeded → LocalLLMContextError
        - Other → LocalLLMError
        """
        if isinstance(error, httpx.ConnectError):
            url = error.request.url if error.request else "unknown"
            return LocalLLMConnectionError(
                f"Cannot connect to local LLM backend at {url}",
                error_code="CONNECTION_ERROR",
            )
        if status_code is not None:
            if status_code in (400, 404, 422):
                msg = response_text or f"HTTP {status_code}"
                if "context" in msg.lower() or "token" in msg.lower():
                    return LocalLLMContextError(msg, error_code="CONTEXT_EXCEEDED")
                return LocalLLMModelError(msg, error_code="MODEL_ERROR")
            if status_code >= HTTP_STATUS_SERVER_ERROR:
                return LocalLLMError(
                    f"Local LLM backend error: HTTP {status_code}",
                    error_code="BACKEND_ERROR",
                )
        return LocalLLMError(str(error), error_code="UNKNOWN")

    async def generate(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
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
            LocalLLMConnectionError: If the backend is unreachable and not in stub mode.
            LocalLLMModelError: If the model is unsupported.
            LocalLLMContextError: If the context window is exceeded.
        """
        if not self._initialized:
            await self.initialize()

        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")

        # If in stub mode, return a stub response immediately
        if self._stub_mode:
            logger.info("Local LLM backend unavailable; returning stub response")
            return self._generate_stub_response(messages)

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
                last_error = self._classify_error(exc)
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
            except httpx.HTTPStatusError as exc:
                last_error = self._classify_error(
                    exc,
                    status_code=exc.response.status_code,
                    response_text=exc.response.text,
                )
                # Don't retry client errors (4xx) — they won't succeed on retry
                if isinstance(last_error, LocalLLMModelError):
                    raise last_error from exc
                if attempt < self.config.max_retries - 1:
                    delay = min(
                        self.config.base_delay_seconds * (2**attempt),
                        self.config.max_delay_seconds,
                    )
                    await asyncio.sleep(delay)
            except Exception as exc:
                last_error = self._classify_error(exc)
                if attempt < self.config.max_retries - 1:
                    delay = min(
                        self.config.base_delay_seconds * (2**attempt),
                        self.config.max_delay_seconds,
                    )
                    await asyncio.sleep(delay)

        if response is None:
            # Fall back to stub mode on failure
            logger.warning(
                "Local LLM backend at %s unreachable after %d attempts; falling back to stub mode",
                self.config.base_url,
                self.config.max_retries,
            )
            self._stub_mode = True
            return self._generate_stub_response(messages)
        return response

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        temperature: float | None = None,
        thinking_level: str | None = None,
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
        thinking_level: str | None = None,
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
        thinking_level: str | None = None,
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

    async def generate_json(
        self,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Generate a JSON response using the local LLM backend.

        Enables structured output for programmatic use. Sets response_format
        to json_object if supported by the backend.

        Args:
            messages: Chat messages in OpenAI-compatible format.

        Returns:
            Parsed JSON object from the response.

        Raises:
            LocalLLMError: If the response is not valid JSON.
        """
        old_json_mode = self.config.json_mode
        self.config.json_mode = True
        try:
            response = await self.generate(messages)
        finally:
            self.config.json_mode = old_json_mode

        try:
            return cast(dict[str, Any], json.loads(response.content))
        except json.JSONDecodeError as exc:
            raise LocalLLMError(
                f"Local LLM returned invalid JSON: {exc}",
                error_code="INVALID_JSON",
            ) from exc

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
                "json_mode",
            ],
            "initialized": self._initialized,
            "backend_available": self._backend_available,
            "max_input_tokens": self.config.max_input_tokens,
            "max_output_tokens": self.config.max_output_tokens,
        }
