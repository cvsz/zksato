from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ZKSATO_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "zksato"
    environment: Literal["dev", "test", "prod"] = "dev"
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

    database_url: str | None = None
    reconciliation_enabled: bool = True
    reconciliation_interval_seconds: float = Field(default=15.0, ge=1, le=3600)
    metrics_enabled: bool = True

    auth_required: bool = False
    api_keys: str = ""
    rate_limit_per_minute: int = Field(default=600, ge=10, le=100_000)
    allowed_origins: str = ""
    allowed_hosts: str = ""

    market_data_stale_seconds: float = Field(default=10.0, gt=0, le=300)
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
    max_symbol_exposure_pct: float = Field(default=20.0, gt=0, le=100)
    max_spread_pct: float = Field(default=3.0, gt=0, le=100)
    require_stop_loss: bool = True
    allow_equity_short_selling: bool = False
    kill_switch: bool = False

    max_tfex_contracts: int = Field(default=20, ge=1, le=10_000)
    max_tfex_margin_usage_pct: float = Field(default=50.0, gt=0, le=100)

    default_strategy: Literal["ema_cross", "rsi_reversion", "breakout"] = "ema_cross"
    default_order_size: int = Field(default=100, ge=1)
    default_stop_loss_pct: float = Field(default=2.0, gt=0, le=50)
    default_take_profit_pct: float = Field(default=4.0, gt=0, le=100)
    default_watchlist: str = "AOT,PTT,CPALL,KBANK,ADVANC"

    settrade_app_id: str | None = None
    settrade_app_secret: str | None = None
    settrade_broker_id: str | None = None
    settrade_app_code: str = "ALGO_EQ"
    settrade_account_no: str | None = None
    settrade_pin: str | None = None
    settrade_derivatives_account_no: str | None = None

    notification_webhook_url: str | None = None

    @property
    def watchlist(self) -> list[str]:
        return [item.strip().upper() for item in self.default_watchlist.split(",") if item.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]

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
    def settrade_tfex_configured(self) -> bool:
        return all(
            [
                self.settrade_app_id,
                self.settrade_app_secret,
                self.settrade_broker_id,
                self.settrade_derivatives_account_no,
                self.settrade_pin,
            ]
        )

    @property
    def api_key_map(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for raw in self.api_keys.replace(",", ";").split(";"):
            item = raw.strip()
            if not item or ":" not in item:
                continue
            token, role = item.rsplit(":", 1)
            if token.strip() and role.strip():
                result[token.strip()] = role.strip().lower()
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
