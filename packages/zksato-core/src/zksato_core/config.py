"""Config base classes and validation."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource


class BaseConfig(BaseSettings):
    """Base configuration class with TOML file support."""

    model_config = SettingsConfigDict(
        env_prefix="ZKSATO_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Override in subclasses
    _config_files: ClassVar[list[Path]] = []

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, env_settings, dotenv_settings, file_secret_settings)

    @classmethod
    def load(cls, env: str | None = None, config_dir: Path | None = None) -> "BaseConfig":
        """Load config with environment-specific overrides."""
        config_files = [Path("config/settings.toml")]
        if config_dir:
            config_files = [config_dir / "settings.toml"]

        if env:
            env_file = Path(f"config/environments/{env}.toml")
            if config_dir:
                env_file = config_dir / "environments" / f"{env}.toml"
            config_files.append(env_file)

        config_files.append(Path("config/settings.local.toml"))
        if config_dir:
            config_files.append(config_dir / "settings.local.toml")

        # Merge TOML files, then apply env vars
        data: dict[str, Any] = {}
        for f in config_files:
            if f.exists():
                with f.open("rb") as fp:
                    data.update(tomllib.load(fp))

        return cls(**data)

    def to_toml(self) -> str:
        """Export config to TOML string."""
        import tomli_w
        return tomli_w.dumps(self.model_dump())

    def save_local(self, path: Path | None = None) -> None:
        """Save config to local TOML file."""
        if path is None:
            path = Path("config/settings.local.toml")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_toml())


class DatabaseConfig(BaseConfig):
    """Database configuration."""

    url: str = Field(default="sqlite+aiosqlite:///./zksato.db")
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=100)
    echo: bool = False


class RedisConfig(BaseConfig):
    """Redis configuration."""

    url: str = Field(default="redis://localhost:6379/0")
    max_connections: int = Field(default=10, ge=1, le=100)
    socket_timeout: float = Field(default=5.0, gt=0)
    socket_connect_timeout: float = Field(default=5.0, gt=0)


class LoggingConfig(BaseConfig):
    """Logging configuration."""

    level: str = Field(default="INFO")
    json: bool = True
    otel_endpoint: str | None = None
    otel_service_name: str = "zksato"


class AuthConfig(BaseConfig):
    """Authentication configuration."""

    required: bool = False
    api_keys: str = ""
    session_secret: str | None = None
    session_cookie_name: str = "zksato_session"
    session_ttl_seconds: int = Field(default=1800, ge=60, le=86400)
    csrf_required: bool = True
    rate_limit_per_minute: int = Field(default=600, ge=10, le=100000)
    allowed_origins: str = ""
    allowed_hosts: str = ""
    account_allow_list: str = ""
    secret_dir: str = "/run/secrets"


def load_toml_config(config_path: Path) -> dict[str, Any]:
    """Load TOML config file."""
    if not config_path.exists():
        return {}
    with config_path.open("rb") as f:
        return tomllib.load(f)


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two config dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result