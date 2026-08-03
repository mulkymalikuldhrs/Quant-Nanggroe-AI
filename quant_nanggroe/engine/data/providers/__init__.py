"""Data providers package — QNAProviderBase implementations.

Providers are lazily registered with ProviderRegistry. Import here so that
any provider module that defines a QNAProviderBase subclass is discoverable
by the fallback chain.
"""

from quant_nanggroe.engine.data.provider_registry import ProviderRegistry

# Registry singleton (thread-safe)
_registry: ProviderRegistry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Return the singleton provider registry."""
    return _registry


def register_provider(provider):
    """Register a QNAProviderBase instance with the global registry.

    Auto-imports provider modules so they register on first access (ponytail:
lazy import, no cost if YahooPolars is never used).
    """
    _registry.register(provider)
    return provider


def auto_register_all():
    """Register all available providers.

    Called once at app startup (or on first registry access). Each provider
    module is imported lazily so optional deps (polars, yfinance) that are
    missing only affect that provider, not the whole system.
    """
    from quant_nanggroe.engine.data.providers.yahoo_polars import (
        YahooPolarsProvider,
    )
    register_provider(YahooPolarsProvider())
