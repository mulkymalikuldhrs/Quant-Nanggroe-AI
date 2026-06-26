"""Data module for Quant Nanggroe AI.

Unified data interface with multi-provider support, automatic failover,
in-memory caching, data freshness monitoring, survivorship bias detection,
and real-time data subscriptions.
"""

from quant_nanggroe.data.cache import DataCache
from quant_nanggroe.data.data_manager import (
    CACHE_TTL,
    MAX_RETRIES,
    RETRY_BACKOFF,
    CacheEntry,
    DataManager,
    DataProvider,
    ProviderType,
)
from quant_nanggroe.data.monitor import DataFreshnessMonitor, FreshnessReport, SymbolFreshness
from quant_nanggroe.data.survivorship import SurvivorshipBiasDetector, BiasReport

__all__ = [
    "CACHE_TTL",
    "MAX_RETRIES",
    "RETRY_BACKOFF",
    "CacheEntry",
    "DataCache",
    "DataFreshnessMonitor",
    "DataManager",
    "DataProvider",
    "FreshnessReport",
    "ProviderType",
    "SurvivorshipBiasDetector",
    "BiasReport",
    "SymbolFreshness",
]
