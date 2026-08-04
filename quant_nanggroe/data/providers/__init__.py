"""Data provider implementations package.

Providers with optional third-party dependencies (alpha_vantage, twelvedata
→ httpx; polygon → polygon-api-client; openbb_mcp → openbb; lse → lse) are
imported lazily and guarded so `import quant_nanggroe.data` never breaks when
an optional dep or API key is missing. Each provider is key-gated: it only
registers when its API key is present in the environment (fail-closed).
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
    # Revived optional providers (key-gated, fail-closed import)
    'alpha_vantage',
    'fred',
    'polygon',
    'twelvedata',
    'openbb_mcp',
    'lse_provider',
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

# Guarded imports — optional-dep / key-gated providers. If a dependency or API
# key is missing, the provider simply stays unimported (fail-closed: the rest
# of the stack keeps working). No silent mock, no crash on import.
import logging as _logging
_logger = _logging.getLogger(__name__)

def _guard_import(modname: str) -> object | None:
    try:
        import importlib
        return importlib.import_module(f"quant_nanggroe.data.providers.{modname}")
    except Exception as _e:  # noqa: BLE001 - intentional fail-closed
        _logger.info("provider %s not loaded (optional dep/key missing): %s", modname, _e)
        return None

_alpha_vantage = _guard_import("alpha_vantage")
_fred = _guard_import("fred")
_polygon = _guard_import("polygon")
_twelvedata = _guard_import("twelvedata")
_openbb_mcp = _guard_import("openbb_mcp")
_lse_provider = _guard_import("lse_provider")
