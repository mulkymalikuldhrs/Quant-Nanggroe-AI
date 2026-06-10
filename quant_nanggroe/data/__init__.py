"""Data access layer for Quant Nanggroe AI.

Provides unified access to market data across multiple providers
with automatic failover, caching, and data normalization.
"""

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.data.manager import DataProviderManager

__all__ = ["DataProvider", "DataProviderManager"]
