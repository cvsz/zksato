"""Config base classes and validation."""

from __future__ import annotations

import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, Literal

import tomli_w
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


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
        _settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings, env_settings, dotenv_settings, file_secret_settings)

    @classmethod
    def load(cls, env: str | None = None, config_dir: Path | None = None) -> BaseConfig:
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
        return tomli_w.dumps(self.model_dump())

    def save_local(self, path: Path | None = None) -> None:
        """Save config to local TOML file."""
        if path is None:
            path = Path("config/settings.local.toml")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_toml())


class LocalLLMBackend(StrEnum):
    """Supported local LLM backends.

    All backends expose an OpenAI-compatible /v1/chat/completions endpoint.
    All inference runs on-premise — no data leaves the local machine.
    """

    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"
    VLLM = "vllm"
    TGI = "tgi"
    OPENAI_COMPATIBLE = "openai_compatible"


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
    json: bool = True  # type: ignore[assignment]  # overrides BaseModel.json method intentionally
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


class Settings(BaseConfig):
    """Main application settings."""

    app_name: str = "zksato"
    environment: Literal["dev", "test", "uat", "prod"] = "dev"
    trading_mode: Literal["paper", "sandbox", "live"] = "paper"
    live_trading_enabled: bool = False
    live_requires_confirmation: bool = True
    live_confirmation_token: str | None = None
    legacy_live_token_enabled: bool = False
    live_approval_ttl_seconds: int = Field(default=120, ge=15, le=3600)
    require_distinct_approver: bool = True
    automation_enabled: bool = True
    dashboard_enabled: bool = True
    poll_interval_seconds: float = Field(default=2.0, ge=0.25, le=60)
    initial_cash: float = Field(default=500_000.0, gt=0)
    paper_match_resting_limits: bool = True
    paper_max_fill_quantity_per_quote: int = Field(default=0, ge=0, le=10_000_000)
    paper_price_improvement: bool = True

    database_url: str | None = None
    redis_url: str | None = None
    coordination_lock_ttl_seconds: int = Field(default=30, ge=5, le=600)
    reconciliation_enabled: bool = True
    reconciliation_interval_seconds: float = Field(default=15.0, ge=1, le=3600)
    metrics_enabled: bool = True

    market_data_stale_seconds: float = Field(default=10.0, gt=0, le=300)
    market_timezone: str = "Asia/Bangkok"
    equity_sessions: str = "09:30-12:30,14:00-16:30"
    equity_holidays: str = ""
    equity_special_sessions_json: str = ""
    enforce_market_sessions: bool = False
    instrument_metadata_json: str = ""
    strict_reference_data: bool = False
    max_positions: int = Field(default=5, ge=1, le=100)
    max_position_pct: float = Field(default=10.0, gt=0, le=100)
    max_risk_per_trade_pct: float = Field(default=0.5, gt=0, le=20)
    max_daily_loss_pct: float = Field(default=2.0, gt=0, le=100)
    max_drawdown_pct: float = Field(default=5.0, gt=0, le=100)
    max_orders_per_day: int = Field(default=50, ge=1, le=10_000)
    max_open_orders: int = Field(default=20, ge=1, le=10_000)
    max_notional_per_order: float = Field(default=100_000.0, gt=0)
    max_price_deviation_pct: float = Field(default=10.0, gt=0, le=100)
    max_gross_exposure_pct: float = Field(default=80.0, gt=0, le=500)
    max_net_exposure_pct: float = Field(default=80.0, gt=0, le=500)
    max_symbol_exposure_pct: float = Field(default=20.0, gt=0, le=100)
    max_sector_exposure_pct: float = Field(default=35.0, gt=0, le=100)
    max_spread_pct: float = Field(default=3.0, gt=0, le=100)
    max_consecutive_broker_errors: int = Field(default=5, ge=1, le=100)
    require_stop_loss: bool = True
    allow_equity_short_selling: bool = False
    kill_switch: bool = False

    settrade_app_id: str | None = None
    settrade_app_secret: str | None = None
    settrade_broker_id: str | None = None
    settrade_app_code: str | None = None
    settrade_account_no: str | None = None
    settrade_pin: str | None = None
    settrade_derivatives_account_no: str | None = None

    ccxt_enabled: bool = False
    ccxt_exchanges: str = ""
    ccxt_sandbox: bool = True
    ccxt_binance_api_key: str | None = None
    ccxt_binance_secret: str | None = None
    ccxt_binanceth_api_key: str | None = None
    ccxt_binanceth_secret: str | None = None
    ccxt_kucoin_api_key: str | None = None
    ccxt_kucoin_secret: str | None = None
    ccxt_kucoin_passphrase: str | None = None
    ccxt_okx_api_key: str | None = None
    ccxt_okx_secret: str | None = None
    ccxt_okx_passphrase: str | None = None
    ccxt_bybit_api_key: str | None = None
    ccxt_bybit_secret: str | None = None

    prediction_enabled: bool = False
    prediction_venue: str = "polymarket"
    prediction_max_order_usd: float = Field(default=10.0, gt=0)
    prediction_enable_live: bool = False
    prediction_clob_url: str = "https://clob.polymarket.com"
    prediction_clob_api_key: str | None = None
    prediction_clob_api_secret: str | None = None
    prediction_clob_passphrase: str | None = None
    prediction_clob_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    max_directional_residual: float = Field(default=100.0, ge=0)
    max_complete_set_cost: float = Field(default=1.0, gt=0)
    min_prediction_edge: float = Field(default=0.03, ge=0, le=1)

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-4-hydrogen"
    gemini_thinking_level: str = "high"
    gemini_max_input_tokens: int = Field(default=1_000_000, gt=0)
    gemini_max_output_tokens: int = Field(default=1_000_000, gt=0)
    gemini_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    gemini_max_retries: int = Field(default=3, ge=1, le=10)

    # Local LLM configuration (offline/private inference)
    local_llm_backend: str = "ollama"
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.2:3b"
    local_llm_api_key: str | None = None
    local_llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    local_llm_max_input_tokens: int = Field(default=4096, gt=0)
    local_llm_max_output_tokens: int = Field(default=2048, gt=0)
    local_llm_max_retries: int = Field(default=3, ge=1, le=10)
    local_llm_timeout_seconds: float = Field(default=60.0, gt=0)

    @property
    def settrade_configured(self) -> bool:
        return all(
            [
                self.settrade_app_id,
                self.settrade_app_secret,
                self.settrade_broker_id,
                self.settrade_account_no,
                self.settrade_pin,
            ]
        )

    @property
    def ccxt_configured(self) -> bool:
        return bool(self.ccxt_enabled and self.ccxt_exchanges.strip())

    @property
    def ccxt_exchange_list(self) -> list[str]:
        return [item.strip().lower() for item in self.ccxt_exchanges.split(",") if item.strip()]

    def ccxt_credentials_for(self, exchange: str) -> tuple[str | None, str | None, str | None]:
        normalized = exchange.strip().lower()
        key_field = f"ccxt_{normalized}_api_key"
        secret_field = f"ccxt_{normalized}_secret"
        passphrase_field = f"ccxt_{normalized}_passphrase"
        key = getattr(self, key_field, None)
        secret = getattr(self, secret_field, None)
        passphrase = getattr(self, passphrase_field, None)
        return key, secret, passphrase

    @property
    def gemini_configured(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.gemini_api_key)

    @property
    def local_llm_configured(self) -> bool:
        """Check if local LLM backend is configured."""
        return bool(self.local_llm_base_url)

    def local_llm_backend_enum(self) -> LocalLLMBackend:
        """Get the local LLM backend as a LocalLLMBackend enum."""
        try:
            return LocalLLMBackend(self.local_llm_backend)
        except ValueError:
            return LocalLLMBackend.OLLAMA


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
