#!/usr/bin/env python3
"""Tests: DataCache — SQLite-backed persistent cache with TTL.

Run: python3 -m unittest tests/test_cache.py -v
"""

from __future__ import annotations

import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import shutil
import tempfile
import time

from quant_nanggroe.data.cache import DataCache, _default_db_path


class TestDataCacheInit(unittest.TestCase):
    """Tests for DataCache construction."""

    def test_default_max_entries(self):
        cache = DataCache()
        self.assertEqual(cache._max_entries, 10_000)
        cache.close()

    def test_custom_db_path(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite") as f:
            cache = DataCache(db_path=f.name)
            self.assertEqual(cache._db_path, f.name)
            cache.close()

    def test_custom_max_entries(self):
        cache = DataCache(max_entries=100)
        self.assertEqual(cache._max_entries, 100)
        cache.close()

    def test_context_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cache.sqlite")
            with DataCache(db_path=path) as cache:
                cache.set("key", "val")
                self.assertEqual(cache.get("key"), "val")

    def test_default_db_path_is_str(self):
        path = _default_db_path()
        self.assertIsInstance(path, str)
        self.assertTrue(path.endswith(".sqlite"))


class TestDataCacheSetGet(unittest.TestCase):
    """Tests for set() and get()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test_cache.sqlite")
        self.cache = DataCache(db_path=self.db_path)

    def tearDown(self):
        self.cache.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_set_and_get_string(self):
        self.cache.set("key1", "hello")
        self.assertEqual(self.cache.get("key1"), "hello")

    def test_set_and_get_dict(self):
        val = {"price": 42000, "change": 0.05}
        self.cache.set("price:btc", val)
        self.assertEqual(self.cache.get("price:btc"), val)

    def test_set_and_get_list(self):
        val = [1, 2, 3, 4, 5]
        self.cache.set("list", val)
        self.assertEqual(self.cache.get("list"), val)

    def test_set_and_get_int(self):
        self.cache.set("int_key", 42)
        self.assertEqual(self.cache.get("int_key"), 42)

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.cache.get("nonexistent"))

    def test_get_expired_returns_none(self):
        self.cache.set("expires_soon", "val", ttl=0)
        time.sleep(0.01)
        self.assertIsNone(self.cache.get("expires_soon"))

    def test_get_not_expired_returns_value(self):
        self.cache.set("persistent", "val", ttl=60)
        self.assertEqual(self.cache.get("persistent"), "val")

    def test_get_empty_string(self):
        self.cache.set("empty", "")
        self.assertEqual(self.cache.get("empty"), "")

    def test_get_none_value(self):
        self.cache.set("none_val", None)
        self.assertIsNone(self.cache.get("none_val"))

    def test_set_overwrite(self):
        self.cache.set("key", "first")
        self.cache.set("key", "second")
        self.assertEqual(self.cache.get("key"), "second")


class TestDataCacheDelete(unittest.TestCase):
    """Tests for delete()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "delete_cache.sqlite")
        self.cache = DataCache(db_path=self.db_path)

    def tearDown(self):
        self.cache.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_delete_existing(self):
        self.cache.set("key", "val")
        self.cache.delete("key")
        self.assertIsNone(self.cache.get("key"))

    def test_delete_missing_does_not_raise(self):
        self.cache.delete("nonexistent")

    def test_delete_then_reinsert(self):
        self.cache.set("key", "val1")
        self.cache.delete("key")
        self.cache.set("key", "val2")
        self.assertEqual(self.cache.get("key"), "val2")


class TestDataCacheClearNamespace(unittest.TestCase):
    """Tests for clear_namespace()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "namespace_cache.sqlite")
        self.cache = DataCache(db_path=self.db_path)

    def tearDown(self):
        self.cache.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_clear_single_namespace(self):
        self.cache.set("ns1:key1", "a")
        self.cache.set("ns1:key2", "b")
        self.cache.set("ns2:key1", "c")
        self.cache.clear_namespace("ns1")
        self.assertIsNone(self.cache.get("ns1:key1"))
        self.assertIsNone(self.cache.get("ns1:key2"))
        self.assertEqual(self.cache.get("ns2:key1"), "c")

    def test_clear_with_special_chars(self):
        self.cache.set("test-key", "val")
        self.cache.clear_namespace("test-key")
        self.assertIsNone(self.cache.get("test-key"))

    def test_clear_non_existent_namespace(self):
        self.cache.clear_namespace("doesnotexist")

    def test_clear_partial_prefix(self):
        self.cache.set("crypto:btc", "btc_val")
        self.cache.set("crypto:eth", "eth_val")
        self.cache.set("stock:aapl", "aapl_val")
        self.cache.clear_namespace("crypto")
        self.assertIsNone(self.cache.get("crypto:btc"))
        self.assertIsNone(self.cache.get("crypto:eth"))
        self.assertEqual(self.cache.get("stock:aapl"), "aapl_val")


class TestDataCacheStats(unittest.TestCase):
    """Tests for stats()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "stats_cache.sqlite")
        self.cache = DataCache(db_path=self.db_path)

    def tearDown(self):
        self.cache.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_stats_empty_cache(self):
        stats = self.cache.stats()
        self.assertEqual(stats["total_entries"], 0)
        self.assertEqual(stats["active_entries"], 0)
        self.assertIsInstance(stats["db_size_mb"], float)

    def test_stats_with_entries(self):
        self.cache.set("key1", "val1")
        self.cache.set("key2", "val2")
        stats = self.cache.stats()
        self.assertEqual(stats["total_entries"], 2)
        self.assertEqual(stats["active_entries"], 2)

    def test_stats_with_expired_entries(self):
        self.cache.set("expired", "val", ttl=0)
        time.sleep(0.01)
        stats = self.cache.stats()
        self.assertEqual(stats["active_entries"], 0)


class TestDataCacheClear(unittest.TestCase):
    """Tests for clear()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "clear_cache.sqlite")
        self.cache = DataCache(db_path=self.db_path)

    def tearDown(self):
        self.cache.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_clear_all_entries(self):
        self.cache.set("a", 1)
        self.cache.set("b", 2)
        self.cache.set("c", 3)
        self.cache.clear()
        self.assertIsNone(self.cache.get("a"))
        self.assertIsNone(self.cache.get("b"))
        self.assertIsNone(self.cache.get("c"))
        stats = self.cache.stats()
        self.assertEqual(stats["total_entries"], 0)

    def test_clear_empty_cache(self):
        self.cache.clear()


class TestDataCacheAutoVacuum(unittest.TestCase):
    """Tests for _maybe_vacuum."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "vacuum_cache.sqlite")
        self.cache = DataCache(db_path=self.db_path, max_entries=5)

    def tearDown(self):
        self.cache.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_vacuum_does_not_remove_under_limit(self):
        for i in range(5):
            self.cache.set(f"key{i}", f"val{i}")
        stats = self.cache.stats()
        self.assertEqual(stats["total_entries"], 5)

    def test_vacuum_removes_expired_first(self):
        self.cache.set("expired", "val", ttl=0)
        time.sleep(0.01)
        for i in range(5):
            self.cache.set(f"key{i}", f"val{i}")
        stats = self.cache.stats()
        self.assertLessEqual(stats["total_entries"], 5)

    def test_vacuum_removes_oldest_when_over_limit(self):
        for i in range(10):
            self.cache.set(f"key{i}", f"val{i}")
        stats = self.cache.stats()
        self.assertLessEqual(stats["total_entries"], 5)


class TestDataCacheSerialization(unittest.TestCase):
    """Tests for JSON serialization edge cases."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "ser_cache.sqlite")
        self.cache = DataCache(db_path=self.db_path)

    def tearDown(self):
        self.cache.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_set_bool(self):
        self.cache.set("flag", True)
        self.assertEqual(self.cache.get("flag"), True)

    def test_set_float(self):
        self.cache.set("pi", 3.14159)
        self.assertAlmostEqual(self.cache.get("pi"), 3.14159)

    def test_set_nested_dict(self):
        val = {"a": 1, "b": {"c": [1, 2, 3], "d": "str"}}
        self.cache.set("nested", val)
        self.assertEqual(self.cache.get("nested"), val)

    def test_set_with_default_str_date(self):
        from datetime import date
        val = {"date": date(2025, 1, 1)}
        self.cache.set("date_key", val)
        retrieved = self.cache.get("date_key")
        self.assertIsInstance(retrieved["date"], str)
        self.assertIn("2025", retrieved["date"])


class TestDataCacheEdgeCases(unittest.TestCase):
    """Tests for edge cases."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "edge_cache.sqlite")
        self.cache = DataCache(db_path=self.db_path)

    def tearDown(self):
        self.cache.close()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_large_key(self):
        key = "x" * 1000
        self.cache.set(key, "val")
        self.assertEqual(self.cache.get(key), "val")

    def test_large_value(self):
        val = {"data": "x" * 10000}
        self.cache.set("large", val)
        self.assertEqual(self.cache.get("large"), val)

    def test_set_same_key_multiple_times(self):
        for i in range(10):
            self.cache.set("key", i)
        self.assertEqual(self.cache.get("key"), 9)

    def test_close_then_reopen(self):
        self.cache.set("persistent", "val")
        self.cache.close()
        cache2 = DataCache(db_path=self.db_path)
        self.assertEqual(cache2.get("persistent"), "val")
        cache2.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
