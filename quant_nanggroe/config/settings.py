"""
Application settings using Pydantic Settings.

All configuration is loaded from environment variables with sensible defaults.
API keys, database URLs, and other secrets MUST be set via environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    All values are loaded from environment variables with the prefix QNAI_.
    For example, QNAI_DATABASE_URL maps to database_url.

    Attributes:
        app_name: Application name
        version: Application version
        debug: Enable debug mode
        database_url: SQLAlchemy database connection URL
        redis_url: Redis connection URL for caching
        openai_api_key: OpenAI API key
        anthropic_api_key: Anthropic API key
        google_api_key: Google AI API key
        alpaca_api_key: Alpaca trading API key
        alpaca_api_secret: Alpaca trading API secret
        binance_api_key: Binance API key
        binance_api_secret: Binance API secret
        alpha_vantage_api_key: Alpha Vantage API key (free tier: 25 req/day)
        polygon_api_key: Polygon.io API key
        fred_api_key: FRED API key (free, 120 req/min)
        coingecko_api_key: CoinGecko Pro API key (free tier works without key)
        finnhub_api_key: Finnhub API key (free tier: 60 calls/min)
        twelvedata_api_key: Twelve Data API key (free tier: 800 credits/day)
        sec_edgar_user_email: SEC EDGAR User-Agent email (required, no key needed)
        ecb_api_key: ECB API key (not needed, API is free)
        default_llm_provider: Default LLM provider
        default_llm_model: Default LLM model name
        log_level: Logging level
        risk_max_per_trade: Maximum risk percentage per trade (constitutional)
        risk_max_daily_loss: Maximum daily loss percentage (constitutional)
        risk_max_weekly_loss: Maximum weekly loss percentage (constitutional)
        risk_max_drawdown: Maximum drawdown percentage (constitutional)
    """

    model_config = SettingsConfigDict(
        env_prefix="QNAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Quant Nanggroe AI"
    version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///quant_nanggroe.db"
    redis_url: Optional[str] = None

    # LLM API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # Trading API Keys
    alpaca_api_key: Optional[str] = None
    alpaca_api_secret: Optional[str] = None
    alpaca_paper: bool = True
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None

    # MetaTrader 5 (multi-account). QNAI_MT5_ACCOUNTS = JSON list of
    # {"login":<int>,"password":<str>,"server":<str>,"role":<"primary"|"failover">}
    mt5_accounts: Optional[str] = None
    mt5_enabled: bool = False

    # Data Provider API Keys (free tiers available)
    alpha_vantage_api_key: Optional[str] = None
    polygon_api_key: Optional[str] = None
    fred_api_key: Optional[str] = None
    coingecko_api_key: Optional[str] = None      # Pro tier (free works without key)
    finnhub_api_key: Optional[str] = None         # Free tier: 60 calls/min
    twelvedata_api_key: Optional[str] = None       # Free tier: 800 credits/day
    sec_edgar_user_email: Optional[str] = None     # Required User-Agent email (no key needed)
    ecb_api_key: Optional[str] = None              # Not needed (ECB is free, no key)

    # LLM Defaults
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o"
    default_llm_temperature: float = 0.0

    # NVIDIA NIM
    nvidia_nim_api_key: Optional[str] = None
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_default_model: str = "meta/llama-3.1-70b-instruct"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Constitutional Risk Limits (CANNOT be overridden by agents)
    risk_max_per_trade: float = Field(
        default=0.5,
        description="Maximum risk percentage per trade. Constitutional limit.",
        ge=0.1,
        le=2.0,
    )
    risk_max_daily_loss: float = Field(
        default=1.0,
        description="Maximum daily loss percentage. Constitutional limit.",
        ge=0.5,
        le=5.0,
    )
    risk_max_weekly_loss: float = Field(
        default=3.0,
        description="Maximum weekly loss percentage. Constitutional limit.",
        ge=1.0,
        le=10.0,
    )
    risk_max_drawdown: float = Field(
        default=10.0,
        description="Maximum drawdown percentage. Constitutional limit.",
        ge=5.0,
        le=20.0,
    )

    # Backtesting
    backtest_default_commission: float = 0.001
    backtest_default_slippage: float = 0.0005
    backtest_default_initial_capital: float = 100000.0

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"],
        description="Allowed CORS origins. Never use wildcard with credentials.",
    )
    cors_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        description="Allowed CORS HTTP methods.",
    )
    cors_headers: list[str] = Field(
        default=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
        description="Allowed CORS request headers.",
    )

    # Security
    # Sentinel default. NOT a usable secret — booting with this value raises
    # (see create_app / boot_security_check). Set QNAI_JWT_SECRET in production.
    jwt_secret: str = Field(
        default="__UNSET_QNAI_JWT_SECRET__",
        description="JWT HMAC secret key. MUST be set via QNAI_JWT_SECRET; "
                    "refusing to boot with the unset sentinel.",
    )

    # Data
    data_cache_ttl: int = 300  # 5 minutes
    data_provider_timeout: int = 30

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid Python logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}, got {v}")
        return v_upper


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings instance.

    Returns:
        Cached Settings instance loaded from environment variables
    """
    return Settings()
