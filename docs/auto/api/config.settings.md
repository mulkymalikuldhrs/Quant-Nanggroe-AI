# config.settings

## Class: 

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

**Methods:** validate_log_level

*Line: 18*

---

## Function: 

Get cached application settings instance.

Returns:
    Cached Settings instance loaded from environment variables

*Line: 171*

---

## Function: 

Validate log level is a valid Python logging level.

*Line: 161*

---

