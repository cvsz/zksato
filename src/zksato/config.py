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

    max_positions: int = Field(default=5, ge=1)
    max_position_pct: float = Field(default=10.0, gt=0, le=100)
    max_daily_loss_pct: float = Field(default=2.0, gt=0, le=100)
    max_drawdown_pct: float = Field(default=5.0, gt=0, le=100)
    require_stop_loss: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
