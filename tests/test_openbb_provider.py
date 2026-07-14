"""Tests for OpenBB MCP data provider.

All tests mock external calls — no real API key required.

Run: python -m unittest tests/test_openbb_provider.py -v
"""

from __future__ import annotations

import sys
import unittest
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch

import pandas as pd

from quant_nanggroe.data.providers.openbb_mcp import OpenBBMCPProvider


class TestInit(unittest.TestCase):
    """Provider initialisation."""

    def test_provider_initialises(self):
        provider = OpenBBMCPProvider(api_key="test-key")
        self.assertEqual(provider.api_key, "test-key")
        self.assertEqual(provider.base_url, "https://api.openbb.co")

    def test_provider_default_api_key(self):
        with patch.dict("os.environ", {"QNAI_OPENBB_API_KEY": "env-key"}):
            provider = OpenBBMCPProvider()
            self.assertEqual(provider.api_key, "env-key")

    def test_sdk_import_fail_is_graceful(self):
        with patch.dict("sys.modules", {"openbb": None}):
            provider = OpenBBMCPProvider()
            self.assertIsNone(provider._sdk)

    def test_sdk_init_fail_is_graceful(self):
        fake_mod = type(sys)("openbb")
        fake_mod.obb = MagicMock()
        fake_mod.obb.account.login.side_effect = Exception("login failed")
        with patch.dict("sys.modules", {"openbb": fake_mod}):
            provider = OpenBBMCPProvider(api_key="<placeholder>")
            self.assertIsNone(provider._sdk)


class TestFetchOHLCV(unittest.TestCase):
    """fetch_ohlcv behaviour."""

    def test_fetch_returns_empty_dataframe_without_sdk(self):
        """When no SDK and no API key, should return empty DataFrame (graceful degradation)."""
        provider = OpenBBMCPProvider()
        df = provider.fetch_ohlcv("AAPL")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertTrue(df.empty)

    def test_fetch_has_required_columns(self):
        """Empty DataFrame should still have the required columns."""
        provider = OpenBBMCPProvider()
        df = provider.fetch_ohlcv("AAPL")
        for col in ["timestamp", "open", "high", "low", "close", "volume"]:
            self.assertIn(col, df.columns, f"Missing column: {col}")

    def test_fetch_via_rest_mocked_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [
                {"date": "2024-01-02", "open": 181.0, "high": 182.0, "low": 179.5,
                 "close": 181.0, "volume": 55_000_000},
                {"date": "2024-01-03", "open": 182.5, "high": 183.0, "low": 180.5,
                 "close": 182.5, "volume": 48_000_000},
            ]
        }
        mock_resp.raise_for_status.return_value = None

        provider = OpenBBMCPProvider()
        with patch.object(provider, "_sdk", None):
            with patch("requests.get", return_value=mock_resp) as mock_get:
                df = provider.fetch_ohlcv("AAPL", "D1")

        self.assertEqual(len(df), 2)
        self.assertCountEqual(df.columns.tolist(),
                              ["timestamp", "open", "high", "low", "close", "volume"])
        self.assertEqual(df.iloc[0]["open"], 181.0)
        mock_get.assert_called_once()

    def test_fetch_via_rest_empty(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status.return_value = None

        provider = OpenBBMCPProvider()
        with patch.object(provider, "_sdk", None):
            with patch("requests.get", return_value=mock_resp):
                df = provider.fetch_ohlcv("UNKNOWN")

        self.assertTrue(df.empty)
        self.assertCountEqual(df.columns.tolist(),
                              ["timestamp", "open", "high", "low", "close", "volume"])

    def test_fetch_via_rest_http_error(self):
        import requests
        provider = OpenBBMCPProvider()
        with patch.object(provider, "_sdk", None):
            with patch("requests.get", side_effect=requests.RequestException("timeout")):
                df = provider.fetch_ohlcv("AAPL")
        self.assertTrue(df.empty)

    def test_fetch_with_sdk_mocked(self):
        mock_sdk = MagicMock()
        mock_data = MagicMock()
        mock_data.empty = False
        mock_df = pd.DataFrame({
            "date": ["2024-01-02", "2024-01-03"],
            "open": [181.0, 182.5],
            "high": [182.0, 183.0],
            "low": [179.5, 180.5],
            "close": [181.0, 182.5],
            "volume": [55_000_000, 48_000_000],
        })
        mock_data.to_dataframe.return_value = mock_df
        mock_sdk.equity.price.historical.return_value = mock_data

        provider = OpenBBMCPProvider()
        provider._sdk = mock_sdk
        df = provider.fetch_ohlcv("AAPL")

        self.assertEqual(len(df), 2)
        mock_sdk.equity.price.historical.assert_called_once_with(
            symbol="AAPL", provider="yfinance"
        )

    def test_sdk_receives_start_end(self):
        mock_sdk = MagicMock()
        mock_data = MagicMock()
        mock_data.empty = False
        mock_df = pd.DataFrame({
            "date": ["2024-01-02"],
            "open": [181.0], "high": [182.0], "low": [179.5],
            "close": [181.0], "volume": [55_000_000],
        })
        mock_data.to_dataframe.return_value = mock_df
        mock_sdk.equity.price.historical.return_value = mock_data

        provider = OpenBBMCPProvider()
        provider._sdk = mock_sdk
        provider.fetch_ohlcv("AAPL", "D1", datetime(2024, 1, 1), datetime(2024, 1, 31))

        mock_sdk.equity.price.historical.assert_called_once_with(
            symbol="AAPL", provider="yfinance",
            start_date="2024-01-01T00:00:00",
            end_date="2024-01-31T00:00:00",
        )

    def test_rest_url_contains_start_end_timeframe(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status.return_value = None

        provider = OpenBBMCPProvider()
        with patch.object(provider, "_sdk", None):
            with patch("requests.get", return_value=mock_resp) as mock_get:
                provider.fetch_ohlcv("AAPL", "H1", datetime(2024, 1, 1), datetime(2024, 1, 31))

        params = mock_get.call_args[1]["params"]
        self.assertEqual(params["start_date"], "2024-01-01T00:00:00")
        self.assertEqual(params["end_date"], "2024-01-31T00:00:00")
        self.assertEqual(params["interval"], "1h")


class TestDataManagerIntegration(unittest.TestCase):
    """Integration shape expected by DataManager."""

    def test_registerable_with_data_manager(self):
        from quant_nanggroe.data.data_manager import DataManager, ProviderType

        DataManager._instance = None
        dm = DataManager()
        provider = OpenBBMCPProvider()
        dm.register("openbb_mcp", provider, ProviderType.EQUITY, priority=5)
        registered = dm.registered(ProviderType.EQUITY)
        self.assertEqual(len(registered), 1)
        self.assertEqual(registered[0].name, "openbb_mcp")
        self.assertEqual(registered[0].priority, 5)

    def test_data_manager_calls_fetch_ohlcv(self):
        from quant_nanggroe.data.data_manager import DataManager, ProviderType
        from quant_nanggroe.types.market import TimeFrame

        DataManager._instance = None
        dm = DataManager()
        provider = OpenBBMCPProvider()
        dm.register("openbb_mcp", provider, ProviderType.EQUITY, priority=0)

        mock_df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2024-01-02"]),
            "open": [181.0], "high": [182.0], "low": [179.5],
            "close": [181.0], "volume": [55_000_000],
        })

        with patch.object(provider, "_fetch_via_rest", return_value=mock_df):
            df = dm.get_ohlcv("AAPL", TimeFrame.D1, provider_type=ProviderType.EQUITY)

        self.assertFalse(df.empty)
        self.assertCountEqual(df.columns.tolist(),
                              ["timestamp", "open", "high", "low", "close", "volume"])
