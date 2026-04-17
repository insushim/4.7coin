"""Central configuration via pydantic-settings.

All environment-dependent values flow through Settings. Hard limits are enforced
here so downstream code cannot accidentally exceed risk bounds.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ===== 공통 =====
    app_env: Literal["development", "production", "test"] = "development"
    trading_mode: Literal["paper", "live"] = "paper"
    timezone: str = "Asia/Seoul"

    # ===== DB / Cache =====
    database_url: str = "postgresql+asyncpg://quantsage:change_me_strong@localhost:5432/quantsage"
    redis_url: str = "redis://localhost:6379/0"

    # ===== 거래소 =====
    upbit_access_key: str = ""
    upbit_secret_key: str = ""
    upbit_allowed_ips: str = "127.0.0.1"

    bithumb_api_key: str = ""
    bithumb_secret_key: str = ""

    binance_api_key: str = ""
    binance_secret_key: str = ""

    # ===== LLM =====
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # ===== 데이터 =====
    coingecko_api_key: str = ""
    cryptopanic_api_key: str = ""
    glassnode_api_key: str = ""

    # ===== 알림 =====
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    kakao_rest_api_key: str = ""
    discord_webhook_url: str = ""

    # ===== 리스크 (모두 하드 상한) =====
    max_position_pct: float = Field(default=0.25, ge=0.01, le=0.5)
    max_daily_loss_pct: float = Field(default=0.03, ge=0.01, le=0.1)
    max_weekly_loss_pct: float = Field(default=0.08, ge=0.02, le=0.2)
    max_drawdown_pct: float = Field(default=0.15, ge=0.05, le=0.3)
    per_trade_risk_pct: float = Field(default=0.01, ge=0.001, le=0.05)
    kelly_fraction: float = Field(default=0.25, ge=0.05, le=0.5)
    vol_target_annual: float = Field(default=0.20, ge=0.05, le=0.6)
    min_confidence: float = Field(default=0.65, ge=0.5, le=0.95)
    circuit_breaker_5m_pct: float = Field(default=-0.05, ge=-0.2, le=-0.01)
    enable_live_trading: bool = False

    # ===== 보안 =====
    master_key: str = ""
    jwt_secret_key: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    admin_username: str = "admin"
    admin_password: str = "change_me_strong"

    @field_validator("enable_live_trading")
    @classmethod
    def warn_live(cls, v: bool, info) -> bool:
        if v and info.data.get("app_env") != "production":
            # 프로덕션 외에서 live 활성화 방지
            return False
        return v

    @property
    def is_live(self) -> bool:
        return self.trading_mode == "live" and self.enable_live_trading


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
