"""Data access layer for Quant Nanggroe AI.

Provides unified access to market data across multiple providers
with automatic failover, caching, and data normalization, plus
a complete data persistence layer with database, caching, and ORM models.

Submodules
----------
providers:
    Market data provider integrations (Binance, Alpaca, Yahoo, etc.).
manager:
    Data provider manager with automatic failover.
database:
    SQLAlchemy async database layer (init, sessions, health checks).
models:
    SQLAlchemy 2.0 ORM models (User, Trade, Position, etc.).
cache:
    Redis caching layer with in-memory fallback.
repository:
    Repository pattern for async CRUD data access.
"""

# Data providers (market data)
from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.data.manager import DataProviderManager

# Database layer
from quant_nanggroe.data.database import (
    init_db,
    close_db,
    get_db_session,
    check_db_health,
    get_engine,
    get_session_factory,
)

# ORM models
from quant_nanggroe.data.models import (
    Base,
    User,
    Trade,
    Position,
    PortfolioSnapshot,
    AgentLog,
    RiskEvent,
    Strategy,
    BacktestResult,
)

# Cache layer
from quant_nanggroe.data.cache import (
    init_redis,
    close_redis,
    cache_get,
    cache_set,
    cache_delete,
    check_redis_health,
)

# Repositories
from quant_nanggroe.data.repository import (
    TradeRepository,
    PositionRepository,
    StrategyRepository,
    RiskEventRepository,
    PaginatedResult,
)

__all__ = [
    # Providers
    "DataProvider",
    "DataProviderManager",
    # Database
    "init_db",
    "close_db",
    "get_db_session",
    "check_db_health",
    "get_engine",
    "get_session_factory",
    # Models
    "Base",
    "User",
    "Trade",
    "Position",
    "PortfolioSnapshot",
    "AgentLog",
    "RiskEvent",
    "Strategy",
    "BacktestResult",
    # Cache
    "init_redis",
    "close_redis",
    "cache_get",
    "cache_set",
    "cache_delete",
    "check_redis_health",
    # Repositories
    "TradeRepository",
    "PositionRepository",
    "StrategyRepository",
    "RiskEventRepository",
    "PaginatedResult",
]
