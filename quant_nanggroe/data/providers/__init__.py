"""Data provider implementations package.

NOTE: modules are imported lazily at the package level but only those that
actually exist on disk are referenced here. Dangling references to deleted/
moved provider files (alpha_vantage, coingecko, fred, openbb_mcp, polygon,
twelvedata) were removed — they broke `import quant_nanggroe.data` entirely
when the source files were purged. Optional-dependency providers (yahoo,
binance) guard their third-party imports internally so the package imports
cleanly without yfinance/ccxt installed.
"""

# Package init — only reference modules that exist on disk.
__all__ = [
    'alpaca',
    'base',
    'binance',
    'coingecko_provider',
    'crypto_provider',
    'finnhub_provider',
    'macro_provider',
    'sec_edgar',
    'yahoo',
]

from . import (
    alpaca,
    base,
    binance,
    coingecko_provider,
    crypto_provider,
    finnhub_provider,
    macro_provider,
    sec_edgar,
    yahoo,
)
