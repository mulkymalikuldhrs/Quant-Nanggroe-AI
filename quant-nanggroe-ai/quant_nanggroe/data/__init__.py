"""Data access layer for Quant Nanggroe AI.

Provides a unified interface to multiple data providers with
automatic failover, caching, and cross-provider normalization.
"""

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.data.manager import DataProviderManager

__all__ = ["DataProvider", "DataProviderManager"]
