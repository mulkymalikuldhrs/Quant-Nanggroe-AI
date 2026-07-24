"""Data providers: CoinGecko, Finnhub, macro, crypto, and LSE."""

# Package init

__all__ = [
    'coingecko_provider',
    'crypto_provider',
    'data_manager',
    'finnhub_provider',
    'lse_provider',
    'macro_provider',
    'proxy',
    'warp',
]

from . import coingecko_provider
from . import crypto_provider
from . import data_manager
from . import finnhub_provider
# lse_provider is OPTIONAL: requires the `lse-data` client (`pip install lse-data` + LSE_API_KEY).
# Importing it eagerly broke the whole package when lse is absent. Keep it importable on-demand
# via `from quant_nanggroe.providers.lse_provider import LSEProvider` when the dep is present.
try:  # ponytail: optional dep must not break package import
    from . import lse_provider  # noqa: F401
except ImportError:
    pass
from . import macro_provider
from . import proxy
from . import warp
