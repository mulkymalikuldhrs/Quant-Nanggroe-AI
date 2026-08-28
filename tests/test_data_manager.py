#!/usr/bin/env python3
"""Tests: DataManager — singleton, provider registration, get_ohlcv with
failover, caching, subscribe/unsubscribe.

Run: python3 -m unittest tests/test_data_manager.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
from unittest.mock import MagicMock

import pandas as pd

from quant_nanggroe.data.data_manager import (
    CACHE_TTL,
    MAX_RETRIES,
    RETRY_BACKOFF,
    DataManager,
    DataProvider,
    ProviderType,
)
from quant_nanggroe.types.market import TimeFrame


class TestDataManagerSingleton(unittest.TestCase):
    """Tests for DataManager singleton pattern."""

    def test_singleton_returns_same_instance(self):
        dm1 = DataManager()
        dm2 = DataManager()
        self.assertIs(dm1, dm2)

    def test_singleton_reset(self):
        DataManager._instance = None
        dm1 = DataManager()
        DataManager._instance = None
        dm2 = DataManager()
        self.assertIsNot(dm1, dm2)

    def test_only_initialized_once(self):
        DataManager._instance = None
        dm = DataManager()
        self.assertTrue(dm._initialized)

    def test_constants_defined(self):
        self.assertGreater(CACHE_TTL, 0)
        self.assertEqual(MAX_RETRIES, 3)
        self.assertEqual(RETRY_BACKOFF, 2.0)


class TestDataManagerRegister(unittest.TestCase):
    """Tests for register() and registered()."""

    def setUp(self):
        DataManager._instance = None
        DataManager._instance = None
        self.dm = DataManager()

    def tearDown(self):
        DataManager._instance = None

    def test_register_provider(self):
        mock = MagicMock()
        self.dm.register("test_provider", mock, ProviderType.CRYPTO)
        providers = self.dm.registered(ProviderType.CRYPTO)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].name, "test_provider")

    def test_register_multiple_providers_same_type(self):
        mock1 = MagicMock()
        mock2 = MagicMock()
        self.dm.register("p1", mock1, ProviderType.CRYPTO, priority=1)
        self.dm.register("p2", mock2, ProviderType.CRYPTO, priority=0)
        providers = self.dm.registered(ProviderType.CRYPTO)
        self.assertEqual(len(providers), 2)

    def test_register_priorities_are_sorted(self):
        mock1 = MagicMock()
        mock2 = MagicMock()
        self.dm.register("high", mock1, ProviderType.EQUITY, priority=10)
        self.dm.register("low", mock2, ProviderType.EQUITY, priority=0)
        providers = self.dm.registered(ProviderType.EQUITY)
        self.assertEqual(providers[0].name, "low")
        self.assertEqual(providers[1].name, "high")

    def test_register_different_types(self):
        mock = MagicMock()
        self.dm.register("c", mock, ProviderType.CRYPTO)
        self.dm.register("e", mock, ProviderType.EQUITY)
        self.assertEqual(len(self.dm.registered(ProviderType.CRYPTO)), 1)
        self.assertEqual(len(self.dm.registered(ProviderType.EQUITY)), 1)

    def test_registered_all_types(self):
        mock = MagicMock()
        self.dm.register("a", mock, ProviderType.CRYPTO)
        self.dm.register("b", mock, ProviderType.FOREX)
        all_providers = self.dm.registered()
        self.assertEqual(len(all_providers), 2)

    def test_registered_no_providers(self):
        providers = self.dm.registered(ProviderType.CRYPTO)
        self.assertEqual(providers, [])

    def test_register_duplicate_name(self):
        mock = MagicMock()
        self.dm.register("dup", mock, ProviderType.CRYPTO)
        self.dm.register("dup", mock, ProviderType.CRYPTO)
        providers = self.dm.registered(ProviderType.CRYPTO)
        self.assertEqual(len(providers), 2)


class TestDataManagerGetOhlcv(unittest.TestCase):
    """Tests for get_ohlcv()."""

    def setUp(self):
        DataManager._instance = None
        self.dm = DataManager()
        self.symbol = "BTC/USDT"
        self.timeframe = TimeFrame.H1
        self.candle_data = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="h"),
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.5] * 5,
            "volume": [1000.0] * 5,
        })

    def tearDown(self):
        DataManager._instance = None

    def test_get_ohlcv_success(self):
        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv.return_value = self.candle_data
        self.dm.register("binance", mock_provider, ProviderType.CRYPTO)
        result = self.dm.get_ohlcv(self.symbol, self.timeframe)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 5)
        mock_provider.fetch_ohlcv.assert_called_once()

    def test_get_ohlcv_no_providers_raises(self):
        with self.assertRaises(ValueError):
            self.dm.get_ohlcv(self.symbol, self.timeframe)

    def test_get_ohlcv_failover(self):
        primary = MagicMock()
        primary.fetch_ohlcv.side_effect = RuntimeError("API down")
        backup = MagicMock()
        backup.fetch_ohlcv.return_value = self.candle_data
        self.dm.register("primary", primary, ProviderType.CRYPTO, priority=0)
        self.dm.register("backup", backup, ProviderType.CRYPTO, priority=1)
        result = self.dm.get_ohlcv(self.symbol, self.timeframe)
        self.assertIsInstance(result, pd.DataFrame)
        primary.fetch_ohlcv.assert_called()
        backup.fetch_ohlcv.assert_called()

    def test_get_ohlcv_all_providers_fail_raises(self):
        primary = MagicMock()
        primary.fetch_ohlcv.side_effect = RuntimeError("fail")
        self.dm.register("primary", primary, ProviderType.CRYPTO)
        with self.assertRaises(RuntimeError):
            self.dm.get_ohlcv(self.symbol, self.timeframe)

    def test_get_ohlcv_empty_data_skips_provider(self):
        empty_data = pd.DataFrame()
        provider = MagicMock()
        provider.fetch_ohlcv.return_value = empty_data
        self.dm.register("empty", provider, ProviderType.CRYPTO)
        with self.assertRaises(RuntimeError):
            self.dm.get_ohlcv(self.symbol, self.timeframe)

    def test_get_ohlcv_returns_normalized_data(self):
        provider = MagicMock()
        raw = pd.DataFrame({
            "timestamp": [1704067200, 1704070800],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000, 1100],
        })
        provider.fetch_ohlcv.return_value = raw
        self.dm.register("test", provider, ProviderType.CRYPTO)
        result = self.dm.get_ohlcv(self.symbol, self.timeframe)
        self.assertIn("open", result.columns)
        self.assertIn("close", result.columns)
        self.assertIn("volume", result.columns)
        self.assertTrue(pd.api.types.is_float_dtype(result["open"]))

    def test_get_ohlcv_caching(self):
        provider = MagicMock()
        provider.fetch_ohlcv.return_value = self.candle_data
        self.dm.register("cached", provider, ProviderType.CRYPTO)
        result1 = self.dm.get_ohlcv(self.symbol, self.timeframe)
        result2 = self.dm.get_ohlcv(self.symbol, self.timeframe)
        provider.fetch_ohlcv.assert_called_once()
        pd.testing.assert_frame_equal(result1, result2)

    def test_get_ohlcv_cache_expiry(self):
        provider = MagicMock()
        provider.fetch_ohlcv.return_value = self.candle_data
        self.dm.register("expire", provider, ProviderType.CRYPTO)
        self.dm._cache_get = MagicMock(return_value=None)
        self.dm.get_ohlcv(self.symbol, self.timeframe)
        self.dm.get_ohlcv(self.symbol, self.timeframe)
        self.assertEqual(provider.fetch_ohlcv.call_count, 2)

    def test_get_ohlcv_with_date_range(self):
        provider = MagicMock()
        provider.fetch_ohlcv.return_value = self.candle_data
        self.dm.register("range", provider, ProviderType.CRYPTO)
        from datetime import datetime
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 2)
        result = self.dm.get_ohlcv(self.symbol, self.timeframe, start=start, end=end)
        self.assertIsInstance(result, pd.DataFrame)

    def test_get_ohlcv_missing_columns_get_filled(self):
        provider = MagicMock()
        raw = pd.DataFrame({"timestamp": [1704067200], "close": [100.0]})
        provider.fetch_ohlcv.return_value = raw
        self.dm.register("partial", provider, ProviderType.CRYPTO)
        result = self.dm.get_ohlcv(self.symbol, self.timeframe)
        self.assertIn("open", result.columns)
        self.assertIn("high", result.columns)
        self.assertIn("low", result.columns)
        self.assertIn("volume", result.columns)


class TestDataManagerCacheHelpers(unittest.TestCase):
    """Tests for internal cache methods."""

    def setUp(self):
        DataManager._instance = None
        self.dm = DataManager()

    def tearDown(self):
        DataManager._instance = None

    def test_cache_key_format(self):
        key = self.dm._cache_key("BTC/USDT", "1h", "2024-01-01", "2024-01-02", ProviderType.CRYPTO)
        self.assertIn("BTC/USDT", key)
        self.assertIn("1h", key)
        self.assertIn("crypto", key)

    def test_cache_key_no_dates(self):
        key = self.dm._cache_key("BTC/USDT", "1h", None, None, ProviderType.CRYPTO)
        self.assertNotIn("None", key)

    def test_cache_get_missing_returns_none(self):
        self.assertIsNone(self.dm._cache_get("nonexistent"))

    def test_cache_set_and_get(self):
        df = pd.DataFrame({"close": [100.0]})
        self.dm._cache_set("key", df)
        cached = self.dm._cache_get("key")
        pd.testing.assert_frame_equal(cached, df)

    def test_cache_get_expired(self):
        df = pd.DataFrame({"close": [100.0]})
        self.dm._cache_set("key", df)
        entry = self.dm._cache.get("key")
        entry.expires_at = time.time() - 10
        cached = self.dm._cache_get("key")
        self.assertIsNone(cached)

    def test_cache_invalidate_all(self):
        self.dm._cache_set("a", pd.DataFrame())
        self.dm._cache_set("b", pd.DataFrame())
        self.dm._cache_invalidate()
        self.assertEqual(len(self.dm._cache), 0)

    def test_cache_invalidate_symbol(self):
        self.dm._cache_set("BTC/USDT:1h", pd.DataFrame())
        self.dm._cache_set("ETH/USDT:1h", pd.DataFrame())
        self.dm._cache_invalidate("BTC")
        self.assertNotIn("BTC/USDT:1h", self.dm._cache)
        self.assertIn("ETH/USDT:1h", self.dm._cache)


class TestDataManagerSubscribe(unittest.TestCase):
    """Tests for subscribe/unsubscribe/_notify."""

    def setUp(self):
        DataManager._instance = None
        self.dm = DataManager()

    def tearDown(self):
        DataManager._instance = None

    def test_subscribe_adds_callback(self):
        cb = MagicMock()
        self.dm.subscribe("BTC/USDT", cb)
        self.assertIn(cb, self.dm._callbacks["BTC/USDT"])

    def test_unsubscribe_removes_callback(self):
        cb = MagicMock()
        self.dm.subscribe("BTC/USDT", cb)
        self.dm.unsubscribe("BTC/USDT", cb)
        self.assertNotIn(cb, self.dm._callbacks.get("BTC/USDT", []))

    def test_unsubscribe_not_registered(self):
        self.dm.unsubscribe("NONEXISTENT", MagicMock())

    def test_notify_invokes_callbacks(self):
        cb = MagicMock()
        self.dm.subscribe("BTC/USDT", cb)
        candle = pd.DataFrame({"close": [50000.0]})
        self.dm._notify("BTC/USDT", candle)
        cb.assert_called_once_with(candle)

    def test_notify_callback_error_does_not_raise(self):
        def failing_cb(df):
            raise ValueError("fail")
        self.dm.subscribe("BTC/USDT", failing_cb)
        self.dm._notify("BTC/USDT", pd.DataFrame({"close": [50000.0]}))

    def test_notify_only_correct_symbol(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        self.dm.subscribe("BTC", cb1)
        self.dm.subscribe("ETH", cb2)
        self.dm._notify("BTC", pd.DataFrame())
        cb1.assert_called_once()
        cb2.assert_not_called()


class TestDataProviderModel(unittest.TestCase):
    """Tests for DataProvider pydantic model."""

    def test_create_provider(self):
        mock = MagicMock()
        dp = DataProvider(name="test", instance=mock, provider_type=ProviderType.CRYPTO, priority=5)
        self.assertEqual(dp.name, "test")
        self.assertIs(dp.instance, mock)
        self.assertEqual(dp.provider_type, ProviderType.CRYPTO)
        self.assertEqual(dp.priority, 5)

    def test_default_priority_zero(self):
        dp = DataProvider(name="default", instance=MagicMock(), provider_type=ProviderType.EQUITY)
        self.assertEqual(dp.priority, 0)


class TestNormalization(unittest.TestCase):
    """Tests for _normalize classmethod."""

    def test_normalize_timestamp_ints(self):
        df = pd.DataFrame({
            "timestamp": [1704067200, 1704070800],
            "close": [100.0, 101.0],
            "volume": [1000, 1100],
        })
        result = DataManager._normalize(df, "TEST")
        self.assertIn("open", result.columns)
        self.assertIn("high", result.columns)
        self.assertIn("low", result.columns)
        self.assertFalse(result["timestamp"].dt.tz is not None)

    def test_normalize_empty(self):
        df = pd.DataFrame()
        result = DataManager._normalize(df, "TEST")
        self.assertTrue(result.empty)

    def test_normalize_dropna_timestamps(self):
        df = pd.DataFrame({
            "timestamp": [1704067200, None],
            "close": [100.0, 101.0],
        })
        result = DataManager._normalize(df, "TEST")
        self.assertEqual(len(result), 1)

    def test_normalize_sorts_by_timestamp(self):
        df = pd.DataFrame({
            "timestamp": [1704070800, 1704067200],
            "close": [101.0, 100.0],
        })
        result = DataManager._normalize(df, "TEST")
        self.assertTrue((result["timestamp"].diff().iloc[1:] >= pd.Timedelta(0)).all())

    def test_normalize_coerces_numeric(self):
        df = pd.DataFrame({
            "timestamp": [1704067200],
            "open": ["100.5"],
            "high": ["101.5"],
            "low": ["99.5"],
            "close": ["100.5"],
            "volume": ["1000"],
        })
        result = DataManager._normalize(df, "TEST")
        self.assertTrue(pd.api.types.is_float_dtype(result["open"]))
        self.assertTrue(pd.api.types.is_float_dtype(result["volume"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
