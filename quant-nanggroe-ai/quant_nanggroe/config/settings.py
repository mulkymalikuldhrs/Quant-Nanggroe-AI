"""Pydantic Settings for environment-based configuration.

All configuration is driven by environment variables with sensible defaults.
Secrets (API keys) are never hardcoded — always sourced from env vars or .env files.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Priority: env var > .env file > default.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "Quant Nanggroe AI"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", pattern=r"^(development|staging|production)$")
    debug: bool = False

    # ── Logging ──
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_format: str = "json"  # "json" or "text"

    # ── Database ──
    database_url: str = "sqlite:///./data/quant_nanggroe.db"
    database_echo: bool = False

    # ── Redis / Cache ──
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300  # seconds
    cache_enabled: bool = True
    cache_backend: str = Field(default="redis", pattern=r"^(redis|file|memory)$")

    # ── Data Provider API Keys ──
    alpha_vantage_api_key: str = ""
    polygon_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    fred_api_key: str = ""
    coingecko_api_key: str = ""

    # ── Binance ──
    binance_api_key: str = ""
    binance_secret_key: str = ""

    # ── LLM / Agent ──
    openai_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""

    # ── Risk Parameters ──
    max_leverage: float = 3.0
    max_correlation: float = 0.7
    max_exposure_per_asset: float = 0.2
    daily_drawdown_limit: float = 0.05
    var_confidence_level: float = 0.95

    # ── Market State Engine ──
    market_state_min_candles: int = 50
    adx_trending_threshold: float = 25.0
    panic_drop_threshold: float = -0.05
    risk_off_drop_threshold: float = -0.02
    atr_high_volatility_pct: float = 2.5
    atr_low_volatility_pct: float = 0.5

    # ── Pressure Normalization Weights ──
    weight_quant_scanner: float = 0.25
    weight_smc_agent: float = 0.30
    weight_news_sentinel: float = 0.20
    weight_flow_agent: float = 0.25

    # ── AutoSwitch (Failover) ──
    autoswitch_max_retries: int = 3
    autoswitch_retry_delay_ms: int = 2000
    autoswitch_cooldown_ms: int = 60000
    autoswitch_failure_threshold: int = 5


# ── Singleton ──
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings singleton.

    On first call the settings are loaded from the environment / .env.
    Subsequent calls return the same instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
