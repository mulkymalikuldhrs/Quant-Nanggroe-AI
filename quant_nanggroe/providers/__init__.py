"""Legacy providers — DEPRECATED. Use quant_nanggroe.data.providers instead."""

# Removed: coingecko_provider, crypto_provider, finnhub_provider, macro_provider
# (replaced by async versions in data/providers/ with DataProvider ABC).
# Remaining files kept for scripts/setup_warp.sh compatibility:
#   lse_provider.py  — self-referential import, optional dependency
#   proxy.py, warp   — consumed by scripts/setup_warp.sh

__all__ = [
    'lse_provider',
    'proxy',
    'warp',
]

try:
    from . import lse_provider
except ImportError:
    pass
from . import proxy, warp
