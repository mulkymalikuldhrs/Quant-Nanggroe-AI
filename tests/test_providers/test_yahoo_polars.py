"""Unit tests for YahooPolarsProvider (QS018 pilot)."""
import os
import sys
import pytest

# Ponytail: strip hermes venv leak
os.environ.pop("PYTHONPATH", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def test_provider_import():
    """YahooPolarsProvider must be importable."""
    from quant_nanggroe.engine.data.providers.yahoo_polars import YahooPolarsProvider
    assert YahooPolarsProvider is not None


def test_provider_implements_base():
    """YahooPolarsProvider must implement QNAProviderBase."""
    from quant_nanggroe.engine.data.providers.yahoo_polars import YahooPolarsProvider
    from quant_nanggroe.engine.data.provider_interface import QNAProviderBase
    provider = YahooPolarsProvider()
    assert isinstance(provider, QNAProviderBase)


def test_provider_name():
    """Provider name must be 'yahoo_polars'."""
    from quant_nanggroe.engine.data.providers.yahoo_polars import YahooPolarsProvider
    provider = YahooPolarsProvider()
    assert provider.name == "yahoo_polars"


def test_provider_categories():
    """Provider must declare supported categories."""
    from quant_nanggroe.engine.data.providers.yahoo_polars import YahooPolarsProvider
    from quant_nanggroe.engine.data.provider_interface import DataCategory
    provider = YahooPolarsProvider()
    assert DataCategory.EQUITY_OHLCV in provider.categories


def test_provider_fetch_empty_symbol():
    """fetch() on invalid symbol returns DataResponse (never crashes)."""
    from quant_nanggroe.engine.data.providers.yahoo_polars import YahooPolarsProvider
    from quant_nanggre.engine.data.provider_interface import DataRequest, DataCategory
    provider = YahooPolarsProvider()
    request = DataRequest(category=DataCategory.EQUITY_OHLCV, symbol="INVALID_TEST_SYMBOL_12345")
    response = provider.fetch(request)
    assert response.provider == "yahoo_polars"
    assert isinstance(response.results, list)


def test_fetch_ohlcv_pandas_fallback():
    """fetch_ohlcv returns pandas DataFrame when polars not installed."""
    from quant_nanggroe.engine.data.providers.yahoo_polars import fetch_ohlcv
    # Use empty/invalid symbol — should return empty frame, not crash
    df = fetch_ohlcv("INVALID_TEST_SYMBOL_12345", period="1d", interval="1d", as_polars=False)
    import pandas as pd
    assert isinstance(df, pd.DataFrame)


def test_provider_registration():
    """Provider must be registrable via ProviderRegistry."""
    from quant_nanggroe.engine.data.providers.yahoo_polars import YahooPolarsProvider
    from quant_nanggroe.engine.data.provider_registry import ProviderRegistry
    registry = ProviderRegistry()
    provider = YahooPolarsProvider()
    registry.register(provider)
    assert registry.get("yahoo_polars") is provider
    assert "yahoo_polars" in registry.list_providers()
