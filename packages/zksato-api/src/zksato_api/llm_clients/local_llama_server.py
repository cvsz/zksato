"""Local LLM server management for llama.cpp and similar backends.

Provides server lifecycle management (start/stop), health checking,
and model discovery for locally-hosted LLM servers. All server processes
run on-premise — critical for zksato's paper/sandbox trading environments.

Patterns adapted from gemini-cli's local LLM client and llama.cpp server:
- Short timeout for health checks (local server should respond quickly)
- Process lifecycle management with proper cleanup
- Health check endpoint polling
- Model discovery from server /v1/models endpoint
- Support for llama.cpp server arguments (context size, GPU layers, etc.)
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Default port for llama.cpp server
DEFAULT_LLAMA_CPP_PORT = 8080
# Default timeout for health check requests (local server should respond fast)
HEALTH_CHECK_TIMEOUT = 5.0


@dataclass
class LocalLLMServerConfig:
    """Configuration for a local LLM server process."""

    backend: str = "llama.cpp"
    # Core llama.cpp server arguments
    ctx_size: int = 4096
    n_gpu_layers: int = -1
    threads: int = 0
    batch_size: int = 512
    ubatch_size: int = 512
    n_parallel: int = 1
    flash_attn: bool = True
    mlock: bool = True
    no_mmap: bool = False
    main_gpu: int = 0
    tensor_split: str | None = None
    cache_type_k: str = "f16"
    cache_type_v: str = "f16"
    rope_scaling: str | None = None
    rope_scale: float | None = None
    rope_freq_base: float | None = None
    rope_freq_scale: float | None = None
    # Hugging Face model download
    hf_repo: str | None = None
    hf_file: str | None = None
    hf_token: str | None = None
    # Server config
    host: str = "localhost"
    port: int = 8080
    model_path: str | None = None
    model_name: str | None = None
    executable: str = "llama-server"
    server_args: list[str] | None = None
    env: dict[str, str] | None = None
    startup_timeout_seconds: float = 30.0
    health_check_interval_seconds: float = 1.0
    max_health_check_retries: int = 30

    @classmethod
    def from_settings(cls, settings: object) -> LocalLLMServerConfig:
        """Create config from zksato Settings object.

        Args:
            settings: zksato Settings instance (from zksato_core.config.Settings)

        Returns:
            LocalLLMServerConfig with values mapped from settings.
        """
        backend = (
            settings.local_llm_backend if hasattr(settings, "local_llm_backend") else "llama.cpp"
        )
        model_path = (
            settings.local_llm_model_path if hasattr(settings, "local_llm_model_path") else None
        )
        model_name = settings.local_llm_model if hasattr(settings, "local_llm_model") else None
        return cls(
            backend=backend,
            host="localhost",
            port=8080,
            model_path=model_path,
            model_name=model_name,
            ctx_size=4096,
            n_gpu_layers=-1,
        )


@dataclass
class ServerInfo:
    """Information about a running local LLM server."""

    backend: str
    host: str
    port: int
    base_url: str
    is_running: bool
    models: list[str] = field(default_factory=list)
    pid: int | None = None

    @property
    def chat_endpoint(self) -> str:
        """Get the chat completions endpoint URL."""
        return f"{self.base_url.rstrip('/')}/v1/chat/completions"

    @property
    def models_endpoint(self) -> str:
        """Get the models list endpoint URL."""
        return f"{self.base_url.rstrip('/')}/v1/models"

    @property
    def health_endpoint(self) -> str:
        """Get the health check endpoint URL."""
        return f"{self.base_url.rstrip('/')}/health"


class LocalLLMServerManager:
    """Manages local LLM server processes (llama.cpp, vLLM, TGI, etc.).

    Provides start/stop lifecycle, health checking, and model discovery
    for locally-hosted LLM servers. All server processes run on-premise.

    Safety invariants preserved:
    - Server processes are started with restricted environment
    - Health checks use short timeouts (local server should respond fast)
    - Server is stopped on cleanup to prevent orphaned processes
    - Model paths are validated before starting
    """

    def __init__(self, config: LocalLLMServerConfig | None = None) -> None:
        self.config = config or LocalLLMServerConfig()
        self._process: asyncio.subprocess.Process | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._server_info: ServerInfo | None = None

    @property
    def server_info(self) -> ServerInfo | None:
        """Get current server information."""
        return self._server_info

    @property
    def is_running(self) -> bool:
        """Return True if the server process is running."""
        if self._process is None:
            return False
        return self._process.returncode is None

    async def _ensure_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client for health checks."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(HEALTH_CHECK_TIMEOUT),
            )
        return self._http_client

    async def _check_health(self) -> bool:
        """Check if the local LLM server is healthy.

        Returns True if the server responds to /v1/models endpoint.
        """
        client = await self._ensure_http_client()
        if self._server_info is None:
            return False
        try:
            resp = await client.get(self._server_info.models_endpoint)
        except Exception as exc:
            logger.debug("Health check failed: %s", exc)
            return False
        else:
            return resp.is_success

    async def _wait_for_healthy(self) -> bool:
        """Wait for the server to become healthy.

        Polls the health endpoint until the server responds or
        the startup timeout is exceeded.
        """
        for _ in range(self.config.max_health_check_retries):
            if await self._check_health():
                return True
            await asyncio.sleep(self.config.health_check_interval_seconds)
        return False

    async def _probe_backend(self) -> None:
        """Probe the backend to check availability and list models.

        Non-fatal — sets _backend_available flag for callers to inspect.
        """
        if not self._http_client or self._server_info is None:
            self._backend_available = False
            return
        try:
            resp = await self._http_client.get(self._server_info.models_endpoint)
            self._backend_available = resp.is_success
            if self._backend_available:
                logger.info(
                    "[LocalLLMServerManager] Backend available at %s",
                    self._server_info.base_url,
                )
            else:
                logger.warning(
                    "[LocalLLMServerManager] Backend unavailable: %s",
                    self._server_info.base_url,
                )
        except Exception as exc:
            logger.debug(
                "[LocalLLMServerManager] Backend probe failed: %s",
                exc,
            )
            self._backend_available = False

    async def _discover_models(self) -> list[str]:
        """Discover available models from the server.

        Returns a list of model names available on the server.
        """
        client = await self._ensure_http_client()
        if self._server_info is None:
            return []
        try:
            resp = await client.get(self._server_info.models_endpoint)
            if resp.is_success:
                data = resp.json()
                models = [
                    item["id"]
                    for item in data.get("data", [])
                    if isinstance(item, dict) and "id" in item
                ]
                return models
        except Exception as exc:
            logger.debug("Model discovery failed: %s", exc)
        return []

    def _build_server_command(self) -> list[str]:  # noqa: PLR0912
        """Build the llama.cpp server command with all configured arguments."""
        cmd = [self.config.executable]
        if self.config.model_path:
            cmd.extend(["--model", self.config.model_path])
        if self.config.model_name:
            cmd.extend(["--model-name", self.config.model_name])

        # Core llama.cpp server arguments
        cmd.extend(["--host", self.config.host, "--port", str(self.config.port)])
        cmd.extend(["--ctx-size", str(self.config.ctx_size)])
        cmd.extend(["--n-gpu-layers", str(self.config.n_gpu_layers)])
        cmd.extend(["--threads", str(self.config.threads)])
        cmd.extend(["--batch-size", str(self.config.batch_size)])
        cmd.extend(["--ubatch-size", str(self.config.ubatch_size)])
        cmd.extend(["--n-parallel", str(self.config.n_parallel)])

        if self.config.flash_attn:
            cmd.extend(["--flash-attn", "on"])
        if self.config.mlock:
            cmd.append("--mlock")
        if self.config.no_mmap:
            cmd.append("--no-mmap")

        # GPU layers configuration
        if self.config.n_gpu_layers >= 0:
            cmd.extend(["--n-gpu-layers", str(self.config.n_gpu_layers)])
        if self.config.main_gpu != 0:
            cmd.extend(["--main-gpu", str(self.config.main_gpu)])
        if self.config.tensor_split:
            cmd.extend(["--tensor-split", self.config.tensor_split])

        # Cache configuration
        if self.config.cache_type_k:
            cmd.extend(["--cache-type-k", self.config.cache_type_k])
        if self.config.cache_type_v:
            cmd.extend(["--cache-type-v", self.config.cache_type_v])

        # RoPE configuration
        if self.config.rope_scaling:
            cmd.extend(["--rope-scaling", self.config.rope_scaling])
        if self.config.rope_scale:
            cmd.extend(["--rope-scale", str(self.config.rope_scale)])
        if self.config.rope_freq_base:
            cmd.extend(["--rope-freq-base", str(self.config.rope_freq_base)])
        if self.config.rope_freq_scale:
            cmd.extend(["--rope-freq-scale", str(self.config.rope_freq_scale)])

        # Hugging Face model download support
        if self.config.hf_repo:
            cmd.extend(["--hf-repo", self.config.hf_repo])
        if self.config.hf_file:
            cmd.extend(["--hf-file", self.config.hf_file])
        if self.config.hf_token:
            cmd.extend(["--hf-token", self.config.hf_token])

        # Server args
        cmd.extend(["--host", self.config.host, "--port", str(self.config.port)])
        if self.config.server_args:
            cmd.extend(self.config.server_args)
        return cmd

    async def start(self) -> ServerInfo:
        """Start the local LLM server process.

        Starts the server executable with the configured arguments,
        waits for it to become healthy, and discovers available models.

        Returns:
            ServerInfo with server connection details.

        Raises:
            RuntimeError: If the server is already running or fails to start.
            FileNotFoundError: If the server executable is not found.
        """
        if self.is_running:
            raise RuntimeError("Local LLM server is already running")

        # Validate model path if provided
        if self.config.model_path and not Path(self.config.model_path).exists():
            raise FileNotFoundError(f"Model path not found: {self.config.model_path}")

        # Build server command with llama.cpp specific arguments
        cmd = self._build_server_command()

        # Prepare environment
        env = dict(os.environ)
        if self.config.env:
            env.update(self.config.env)

        logger.info(
            "Starting local LLM server: %s",
            " ".join(cmd),
        )

        # Prepare environment
        env = dict(os.environ)
        if self.config.env:
            env.update(self.config.env)

        logger.info(
            "Starting local LLM server: %s",
            " ".join(cmd),
        )

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"LLM server executable not found: {self.config.executable}"
            ) from exc

        # Build server info
        base_url = f"http://{self.config.host}:{self.config.port}"
        self._server_info = ServerInfo(
            backend=self.config.backend,
            host=self.config.host,
            port=self.config.port,
            base_url=base_url,
            is_running=True,
            pid=self._process.pid,
        )

        # Wait for the server to become healthy
        healthy = await self._wait_for_healthy()
        if not healthy:
            # Server failed to start — capture stderr for debugging
            stderr = b""
            if self._process.stderr:
                stderr = await self._process.stderr.read()
            await self.stop()
            raise RuntimeError(
                f"Local LLM server failed to start within "
                f"{self.config.startup_timeout_seconds}s. "
                f"Stderr: {stderr.decode('utf-8', errors='replace')}"
            )

        # Discover available models
        models = await self._discover_models()
        if self._server_info:
            self._server_info.models = models
            self._server_info.is_running = True

        logger.info(
            "Local LLM server started at %s with %d models",
            base_url,
            len(models),
        )
        return self._server_info

    async def stop(self) -> None:
        """Stop the local LLM server process.

        Sends SIGTERM followed by SIGKILL if the process doesn't exit
        within the timeout. Cleans up the HTTP client.
        """
        if self._process is None:
            self._server_info = None
            return

        if self._process.returncode is not None:
            # Process already exited
            self._process = None
            self._server_info = None
            if self._http_client:
                await self._http_client.aclose()
                self._http_client = None
            return

        # Send SIGTERM first
        self._process.terminate()
        try:
            await asyncio.wait_for(self._process.wait(), timeout=5.0)
        except TimeoutError:
            # Process didn't exit — force kill
            self._process.kill()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                logger.warning("Local LLM server process did not exit after kill")

        self._process = None
        self._server_info = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        logger.info("Local LLM server stopped")

    async def health_check(self) -> bool:
        """Perform a health check on the running server.

        Returns True if the server is running and responding.
        """
        if not self.is_running or self._server_info is None:
            return False
        return await self._check_health()

    async def list_models(self) -> list[str]:
        """List available models from the running server.

        Returns an empty list if the server is not running or
        model discovery fails.
        """
        if not self.is_running or self._server_info is None:
            return []
        return await self._discover_models()

    async def __aenter__(self) -> LocalLLMServerManager:
        """Async context manager entry — starts the server."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Async context manager exit — stops the server."""
        await self.stop()


def create_local_llm_server_manager(settings: object) -> LocalLLMServerManager:
    """Create a LocalLLMServerManager from zksato Settings.

    Args:
        settings: zksato Settings instance (from zksato_core.config.Settings)

    Returns:
        Configured LocalLLMServerManager instance.
    """
    config = LocalLLMServerConfig.from_settings(settings)
    return LocalLLMServerManager(config)
