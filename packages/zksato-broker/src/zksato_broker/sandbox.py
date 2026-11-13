"""Sandbox manager for isolated paper/UAT environments."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class SandboxRuntime(str, Enum):
    """Supported sandbox runtimes."""

    DOCKER = "docker"
    PODMAN = "podman"
    LOCAL = "local"


class SandboxStatus(str, Enum):
    """Sandbox lifecycle status."""

    CREATING = "creating"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class SandboxConfig:
    """Configuration for a sandbox environment."""

    name: str
    runtime: SandboxRuntime = SandboxRuntime.DOCKER
    network_isolated: bool = True
    cpu_limit: str = "1.0"
    memory_limit: str = "2g"
    storage_limit: str = "10g"
    environment: dict[str, str] = field(default_factory=dict)
    ports: dict[int, int] = field(default_factory=dict)
    volumes: dict[str, str] = field(default_factory=dict)
    enable_postgres: bool = True
    enable_redis: bool = True
    postgres_version: str = "16"
    redis_version: str = "7"


@dataclass
class Sandbox:
    """Represents a running sandbox environment."""

    id: str
    config: SandboxConfig
    status: SandboxStatus = SandboxStatus.CREATING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    container_id: str | None = None
    postgres_dsn: str | None = None
    redis_url: str | None = None
    api_url: str | None = None
    error: str | None = None


class PaperSandboxConfig(SandboxConfig):
    """Configuration for paper trading sandbox."""

    initial_cash: float = 500_000.0
    match_resting_limits: bool = True
    max_fill_quantity_per_quote: int = 0
    price_improvement: bool = True
    market_data_feed: str = "demo"


class UATSandboxConfig(SandboxConfig):
    """Configuration for UAT sandbox with traffic mirroring."""

    mirror_production: bool = True
    mirror_percentage: float = 0.1
    isolated_credentials: bool = True
    broker: str = "settrade"


class SandboxManager:
    """Manages isolated sandbox environments for paper trading and UAT."""

    def __init__(self, runtime: SandboxRuntime = SandboxRuntime.DOCKER) -> None:
        self.runtime = runtime
        self._sandboxes: dict[str, Sandbox] = {}
        self._lock = asyncio.Lock()

    async def create_paper_sandbox(self, config: PaperSandboxConfig) -> Sandbox:
        """Create isolated paper trading environment."""
        sandbox_id = f"paper-{uuid.uuid4().hex[:8]}"
        sandbox = Sandbox(id=sandbox_id, config=config)

        async with self._lock:
            self._sandboxes[sandbox_id] = sandbox

        try:
            await self._start_sandbox(sandbox)
            sandbox.status = SandboxStatus.RUNNING
            sandbox.started_at = datetime.now(UTC)

            # Configure sandbox-specific services
            await self._configure_paper_sandbox(sandbox, config)

        except Exception as e:
            sandbox.status = SandboxStatus.FAILED
            sandbox.error = str(e)
            raise

        return sandbox

    async def create_uat_sandbox(self, config: UATSandboxConfig) -> Sandbox:
        """Create UAT sandbox with traffic mirroring."""
        sandbox_id = f"uat-{uuid.uuid4().hex[:8]}"
        sandbox = Sandbox(id=sandbox_id, config=config)

        async with self._lock:
            self._sandboxes[sandbox_id] = sandbox

        try:
            await self._start_sandbox(sandbox)
            sandbox.status = SandboxStatus.RUNNING
            sandbox.started_at = datetime.now(UTC)

            # Configure UAT-specific services
            await self._configure_uat_sandbox(sandbox, config)

        except Exception as e:
            sandbox.status = SandboxStatus.FAILED
            sandbox.error = str(e)
            raise

        return sandbox

    async def _start_sandbox(self, sandbox: Sandbox) -> None:
        """Start the sandbox container."""
        if sandbox.config.runtime == SandboxRuntime.LOCAL:
            # Local process-based sandbox
            sandbox.container_id = f"local-{sandbox.id}"
            sandbox.api_url = "http://localhost:9569"
            if sandbox.config.enable_postgres:
                sandbox.postgres_dsn = "postgresql://localhost:5432/zksato_sandbox"
            if sandbox.config.enable_redis:
                sandbox.redis_url = "redis://localhost:6379/1"
            return

        # Docker/Podman sandbox
        runtime_cmd = "docker" if sandbox.config.runtime == SandboxRuntime.DOCKER else "podman"

        # Build container command
        cmd = [
            runtime_cmd,
            "run",
            "-d",
            "--name",
            f"zksato-sandbox-{sandbox.id}",
            "--cpus",
            sandbox.config.cpu_limit,
            "--memory",
            sandbox.config.memory_limit,
        ]

        if sandbox.config.network_isolated:
            cmd.extend(["--network", "none"])

        # Port mappings
        for host_port, container_port in sandbox.config.ports.items():
            cmd.extend(["-p", f"{host_port}:{container_port}"])

        # Volumes
        for host_path, container_path in sandbox.config.volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])

        # Environment variables
        for key, value in sandbox.config.environment.items():
            cmd.extend(["-e", f"{key}={value}"])

        # Default environment
        cmd.extend(
            [
                "-e",
                "ZKSATO_TRADING_MODE=paper",
                "-e",
                f"ZKSATO_SANDBOX_ID={sandbox.id}",
            ]
        )

        # Run the zksato API image
        cmd.append("zksato-api:latest")

        # Execute
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Failed to start sandbox: {stderr.decode()}")

        sandbox.container_id = stdout.decode().strip()

        # Wait for container to be ready
        await asyncio.sleep(2)

        # Get container info
        inspect_cmd = [runtime_cmd, "inspect", sandbox.container_id]
        inspect_proc = await asyncio.create_subprocess_exec(
            *inspect_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        inspect_stdout, _ = await inspect_proc.communicate()

        import json

        inspect_data = json.loads(inspect_stdout.decode())

        # Get IP address
        networks = inspect_data[0].get("NetworkSettings", {}).get("Networks", {})
        for net_info in networks.values():
            ip = net_info.get("IPAddress")
            if ip:
                sandbox.api_url = f"http://{ip}:9569"
                break

        if sandbox.config.enable_postgres:
            sandbox.postgres_dsn = f"postgresql://postgres:postgres@{sandbox.api_url.replace('http://', '').split(':')[0]}:5432/zksato"
        if sandbox.config.enable_redis:
            sandbox.redis_url = (
                f"redis://{sandbox.api_url.replace('http://', '').split(':')[0]}:6379"
            )

    async def _configure_paper_sandbox(self, sandbox: Sandbox, config: PaperSandboxConfig) -> None:
        """Configure paper trading sandbox."""
        # This would configure the sandbox with paper trading settings
        # For now, just set the API URL
        if not sandbox.api_url:
            sandbox.api_url = "http://localhost:9569"

    async def _configure_uat_sandbox(self, sandbox: Sandbox, config: UATSandboxConfig) -> None:
        """Configure UAT sandbox."""
        # This would configure traffic mirroring, isolated credentials, etc.
        if not sandbox.api_url:
            sandbox.api_url = "http://localhost:9569"

    async def stop_sandbox(self, sandbox_id: str) -> None:
        """Stop and remove a sandbox."""
        async with self._lock:
            sandbox = self._sandboxes.get(sandbox_id)
            if not sandbox:
                return

            sandbox.status = SandboxStatus.STOPPING

        try:
            if sandbox.container_id:
                runtime_cmd = (
                    "docker" if sandbox.config.runtime == SandboxRuntime.DOCKER else "podman"
                )
                if not sandbox.container_id.startswith("local-"):
                    proc = await asyncio.create_subprocess_exec(
                        runtime_cmd,
                        "stop",
                        sandbox.container_id,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await proc.communicate()

                    proc = await asyncio.create_subprocess_exec(
                        runtime_cmd,
                        "rm",
                        sandbox.container_id,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await proc.communicate()

            sandbox.status = SandboxStatus.STOPPED
            sandbox.stopped_at = datetime.now(UTC)

        except Exception as e:
            sandbox.status = SandboxStatus.FAILED
            sandbox.error = str(e)
            raise
        finally:
            async with self._lock:
                self._sandboxes.pop(sandbox_id, None)

    async def get_sandbox(self, sandbox_id: str) -> Sandbox | None:
        """Get sandbox by ID."""
        async with self._lock:
            return self._sandboxes.get(sandbox_id)

    async def list_sandboxes(self) -> list[Sandbox]:
        """List all sandboxes."""
        async with self._lock:
            return list(self._sandboxes.values())

    async def cleanup_all(self) -> None:
        """Stop all sandboxes."""
        sandboxes = await self.list_sandboxes()
        for sandbox in sandboxes:
            if sandbox.status == SandboxStatus.RUNNING:
                await self.stop_sandbox(sandbox.id)
