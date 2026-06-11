"""Data Providers — Unified multi-source market data access.

Provides a unified interface to 10+ data providers including
equities, crypto, forex, economic data, and alternative data.
Each provider inherits from DataProvider ABC and can be
individually enabled/disabled via configuration.

Features
--------
* Unified DataProvider interface across all sources
* Provider registry with auto-discovery
* Rate limiting and caching built-in
* Health monitoring per provider
* Graceful degradation when API keys missing
"""

from quant_nanggroe.data.base import (
    DataProvider,
    DataProviderConfig,
    DataResponse,
    DataRequest,
    ProviderRegistry,
    ProviderStatus,
)
from quant_nanggroe.data.manager import DataProviderManager

__all__ = [
    "DataProvider",
    "DataProviderConfig",
    "DataResponse",
    "DataRequest",
    "ProviderRegistry",
    "ProviderStatus",
    "DataProviderManager",
]
