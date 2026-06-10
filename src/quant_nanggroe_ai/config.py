"""
Centralized Configuration — Pydantic Settings
==============================================
All configuration loaded from environment variables with validation.
Constitutional risk limits are HARDCODED and cannot be overridden.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ══════════════════════════════════════════════════════════════════════
# CONSTITUTIONAL RISK LIMITS — HARDCODED, NO OVERRIDE
# ══════════════════════════════════════════════════════════════════════

MAX_RISK_PER_TRADE: float = 0.005       # 0.5% max risk per trade
MAX_DAILY_LOSS: float = 0.01            # 1.0% max daily loss
MAX_WEEKLY_LOSS: float = 0.03           # 3.0% max weekly loss
MIN_RISK_REWARD: float = 2.0            # Minimum 1:2 R:R ratio
MAX_CORRELATED_POSITIONS: int = 3       # Max correlated positions


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(env_prefix="DB_")

    url: str = Field(
        default="postgresql+asyncpg://qna:qna_dev_password@localhost:5432/quant_nanggroe",
        alias="DATABASE_URL",
        description="Async database URL",
    )
    sync_url: str = Field(
        default="postgresql://qna:qna_dev_password@localhost:5432/quant_nanggroe",
        alias="DATABASE_SYNC_URL",
        description="Sync database URL for migrations",
    )
    pool_size: int = Field(default=10, ge=1, le=50)
    max_overflow: int = Field(default=20, ge=0, le=50)
    echo: bool = Field(default=False)


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: str = Field(default="redis://localhost:6379/0")
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")
    default_model: str = Field(default="gpt-4o", alias="DEFAULT_LLM_MODEL")
    default_provider: str = Field(default="openai", alias="DEFAULT_LLM_PROVIDER")


class DataSourceSettings(BaseSettings):
    """Data source API key settings."""

    model_config = SettingsConfigDict(env_prefix="DATA_")

    polygon_api_key: str = Field(default="", alias="POLYGON_API_KEY")
    alpaca_api_key: str = Field(default="", alias="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(default="", alias="ALPACA_SECRET_KEY")
    alpha_vantage_api_key: str = Field(default="", alias="ALPHA_VANTAGE_API_KEY")
    fred_api_key: str = Field(default="", alias="FRED_API_KEY")
    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_secret_key: str = Field(default="", alias="BINANCE_SECRET_KEY")


class FeatureFlags(BaseSettings):
    """Feature flag settings."""

    model_config = SettingsConfigDict(env_prefix="FEATURE_")

    paper_trading: bool = Field(default=True, alias="ENABLE_PAPER_TRADING")
    live_trading: bool = Field(default=False, alias="ENABLE_LIVE_TRADING")
    agents: bool = Field(default=True, alias="ENABLE_AGENTS")
    backtest: bool = Field(default=True, alias="ENABLE_BACKTEST")
    kill_switch: bool = Field(default=True, alias="ENABLE_KILL_SWITCH")
    autoswitch: bool = Field(default=True, alias="ENABLE_AUTOSWITCH")


class Settings(BaseSettings):
    """
    Master application settings.

    Aggregates all sub-settings and provides a single entry point.
    Constitutional risk limits are importable constants, NOT configurable.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Quant-Nanggroe-AI")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="change-me-to-a-secure-random-string")
    debug: bool = Field(default=False)

    # Sub-settings
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    data_sources: DataSourceSettings = Field(default_factory=DataSourceSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    # Trading limits (softer limits — constitutional limits are hardcoded)
    max_open_positions: int = Field(default=10, ge=1, le=50)
    max_trades_per_day: int = Field(default=5, ge=1, le=20)

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}, got '{v}'")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return upper

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


# Singleton settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings (useful for testing)."""
    global _settings
    _settings = None
