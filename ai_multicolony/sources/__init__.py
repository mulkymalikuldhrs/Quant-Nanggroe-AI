"""Intelligence sources package for AI-MultiColony.

Provides OSINT intelligence, economic data feeds, and market data
through a unified SourceProvider interface with orchestration,
deduplication, and relevance scoring.

Modules
-------
base     – SourceProvider base class, data models, enums
osint    – 27-source OSINT intelligence sweep engine
economic – Macroeconomic indicator feeds (GDP, CPI, rates)
market   – Market data feeds (equities, crypto, forex)
manager  – Source orchestration, aggregation, scoring
"""

from .base import (
    SourceCategory,
    SourceConfig,
    SourceItem,
    SourceProvider,
    SourceReliability,
    SourceResult,
    SourceStatus,
)
from .osint import OSINTSource, OSINT_CATEGORIES, SAMPLE_OSINT_DATABASE, OSINT_DATABASE
from .economic import (
    EconomicSource,
    EconomicIndicator,
    GDPRate,
    InflationData,
    InterestRateData,
    ECONOMIC_PROFILES,
    SAMPLE_ECONOMIC_PROFILES,
)
from .market import (
    MarketSource,
    EquityQuote,
    CryptoQuote,
    ForexQuote,
    SAMPLE_EQUITY_DATA,
    SAMPLE_CRYPTO_DATA,
    SAMPLE_FOREX_DATA,
    EQUITY_DATA,
    CRYPTO_DATA,
    FOREX_DATA,
)
from .manager import (
    SourceManager,
    SweepResult,
    AggregatedResult,
)

__all__ = [
    # Base
    "SourceCategory",
    "SourceConfig",
    "SourceItem",
    "SourceProvider",
    "SourceReliability",
    "SourceResult",
    "SourceStatus",
    # OSINT
    "OSINTSource",
    "OSINT_CATEGORIES",
    "SAMPLE_OSINT_DATABASE",
    "OSINT_DATABASE",
    # Economic
    "EconomicSource",
    "EconomicIndicator",
    "GDPRate",
    "InflationData",
    "InterestRateData",
    "ECONOMIC_PROFILES",
    "SAMPLE_ECONOMIC_PROFILES",
    # Market
    "MarketSource",
    "EquityQuote",
    "CryptoQuote",
    "ForexQuote",
    "SAMPLE_EQUITY_DATA",
    "SAMPLE_CRYPTO_DATA",
    "SAMPLE_FOREX_DATA",
    "EQUITY_DATA",
    "CRYPTO_DATA",
    "FOREX_DATA",
    # Manager
    "SourceManager",
    "SweepResult",
    "AggregatedResult",
]
