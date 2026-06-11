"""Comprehensive tests for the persistence layer.

Tests cover all three backends:
- MemoryBackend: basic CRUD, TTL, key patterns, clear
- FileBackend: basic CRUD, TTL, key patterns, health check
- RedisBackend: basic CRUD (graceful skip if Redis unavailable)
- Factory function: get_persistence_backend with env var selection
- RiskManager integration: persistence of risk state across instances
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from datetime import date, datetime
from unittest.mock import patch

import pytest

from quant_nanggroe.engine.persistence import (
    PersistenceBackend,
    MemoryBackend,
    FileBackend,
    RedisBackend,
    get_persistence_backend,
)


# ═══════════════════════════════════════════════════════════════════════════
# MemoryBackend Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMemoryBackend:
    """Tests for the MemoryBackend."""

    def setup_method(self):
        self.backend = MemoryBackend()

    def test_set_and_get(self):
        self.backend.set("test_key", "test_value")
        assert self.backend.get("test_key") == "test_value"

    def test_get_nonexistent(self):
        assert self.backend.get("nonexistent") is None

    def test_get_with_default(self):
        assert self.backend.get_with_default("missing", 42) == 42
        self.backend.set("exists", 99)
        assert self.backend.get_with_default("exists", 42) == 99

    def test_set_various_types(self):
        self.backend.set("int_val", 42)
        self.backend.set("float_val", 3.14)
        self.backend.set("bool_val", True)
        self.backend.set("list_val", [1, 2, 3])
        self.backend.set("dict_val", {"nested": "data"})

        assert self.backend.get("int_val") == 42
        assert self.backend.get("float_val") == 3.14
        assert self.backend.get("bool_val") is True
        assert self.backend.get("list_val") == [1, 2, 3]
        assert self.backend.get("dict_val") == {"nested": "data"}

    def test_overwrite(self):
        self.backend.set("key", "first")
        self.backend.set("key", "second")
        assert self.backend.get("key") == "second"

    def test_delete(self):
        self.backend.set("key", "value")
        assert self.backend.delete("key") is True
        assert self.backend.get("key") is None

    def test_delete_nonexistent(self):
        assert self.backend.delete("nonexistent") is False

    def test_exists(self):
        self.backend.set("key", "value")
        assert self.backend.exists("key") is True
        assert self.backend.exists("nonexistent") is False

    def test_keys_all(self):
        self.backend.set("a", 1)
        self.backend.set("b", 2)
        self.backend.set("c", 3)
        keys = self.backend.keys()
        assert set(keys) == {"a", "b", "c"}

    def test_keys_pattern(self):
        self.backend.set("risk:daily", 1)
        self.backend.set("risk:weekly", 2)
        self.backend.set("colony:state", 3)
        keys = self.backend.keys("risk:*")
        assert set(keys) == {"risk:daily", "risk:weekly"}

    def test_set_many(self):
        mapping = {"k1": "v1", "k2": "v2", "k3": "v3"}
        assert self.backend.set_many(mapping) is True
        assert self.backend.get("k1") == "v1"
        assert self.backend.get("k2") == "v2"
        assert self.backend.get("k3") == "v3"

    def test_delete_many(self):
        self.backend.set("a", 1)
        self.backend.set("b", 2)
        self.backend.set("c", 3)
        count = self.backend.delete_many(["a", "b", "nonexistent"])
        assert count == 2
        assert self.backend.get("a") is None
        assert self.backend.get("c") == 3

    def test_ttl_expiry(self):
        self.backend.set("ttl_key", "value", ttl=1)
        assert self.backend.get("ttl_key") == "value"
        time.sleep(1.1)
        assert self.backend.get("ttl_key") is None

    def test_ttl_no_expiry(self):
        self.backend.set("no_ttl", "value")
        time.sleep(0.1)
        assert self.backend.get("no_ttl") == "value"

    def test_clear(self):
        self.backend.set("a", 1)
        self.backend.set("b", 2)
        self.backend.clear()
        assert self.backend.keys() == []

    def test_health_check(self):
        health = self.backend.health_check()
        assert health["healthy"] is True
        assert health["backend"] == "MemoryBackend"


# ═══════════════════════════════════════════════════════════════════════════
# FileBackend Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestFileBackend:
    """Tests for the FileBackend."""

    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self.backend = FileBackend(data_dir=self._tmpdir)

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_set_and_get(self):
        self.backend.set("test_key", "test_value")
        assert self.backend.get("test_key") == "test_value"

    def test_get_nonexistent(self):
        assert self.backend.get("nonexistent") is None

    def test_get_with_default(self):
        assert self.backend.get_with_default("missing", 42) == 42
        self.backend.set("exists", 99)
        assert self.backend.get_with_default("exists", 42) == 99

    def test_set_various_types(self):
        self.backend.set("int_val", 42)
        self.backend.set("float_val", 3.14)
        self.backend.set("list_val", [1, 2, 3])
        self.backend.set("dict_val", {"nested": "data"})

        assert self.backend.get("int_val") == 42
        assert self.backend.get("float_val") == 3.14
        assert self.backend.get("list_val") == [1, 2, 3]
        assert self.backend.get("dict_val") == {"nested": "data"}

    def test_overwrite(self):
        self.backend.set("key", "first")
        self.backend.set("key", "second")
        assert self.backend.get("key") == "second"

    def test_delete(self):
        self.backend.set("key", "value")
        assert self.backend.delete("key") is True
        assert self.backend.get("key") is None

    def test_delete_nonexistent(self):
        assert self.backend.delete("nonexistent") is False

    def test_exists(self):
        self.backend.set("key", "value")
        assert self.backend.exists("key") is True
        assert self.backend.exists("nonexistent") is False

    def test_keys_all(self):
        self.backend.set("a", 1)
        self.backend.set("b", 2)
        self.backend.set("c", 3)
        keys = self.backend.keys()
        assert set(keys) == {"a", "b", "c"}

    def test_keys_pattern(self):
        self.backend.set("risk:daily", 1)
        self.backend.set("risk:weekly", 2)
        self.backend.set("colony:state", 3)
        keys = self.backend.keys("risk:*")
        assert set(keys) == {"risk:daily", "risk:weekly"}

    def test_set_many(self):
        mapping = {"k1": "v1", "k2": "v2", "k3": "v3"}
        assert self.backend.set_many(mapping) is True
        assert self.backend.get("k1") == "v1"

    def test_delete_many(self):
        self.backend.set("a", 1)
        self.backend.set("b", 2)
        self.backend.set("c", 3)
        count = self.backend.delete_many(["a", "b", "nonexistent"])
        assert count == 2
        assert self.backend.get("a") is None
        assert self.backend.get("c") == 3

    def test_ttl_expiry(self):
        self.backend.set("ttl_key", "value", ttl=1)
        assert self.backend.get("ttl_key") == "value"
        time.sleep(1.5)
        assert self.backend.get("ttl_key") is None

    def test_ttl_no_expiry(self):
        self.backend.set("no_ttl", "value")
        time.sleep(0.1)
        assert self.backend.get("no_ttl") == "value"

    def test_health_check(self):
        health = self.backend.health_check()
        assert health["healthy"] is True
        assert health["backend"] == "FileBackend"

    def test_special_characters_in_key(self):
        self.backend.set("risk:daily_pnl", -500.0)
        self.backend.set("path/to/key", 42)
        assert self.backend.get("risk:daily_pnl") == -500.0
        assert self.backend.get("path/to/key") == 42

    def test_data_dir_creation(self):
        new_dir = os.path.join(self._tmpdir, "subdir", "nested")
        backend = FileBackend(data_dir=new_dir)
        backend.set("test", "value")
        assert backend.get("test") == "value"
        assert os.path.isdir(new_dir)


# ═══════════════════════════════════════════════════════════════════════════
# RedisBackend Tests (graceful skip if Redis unavailable)
# ═══════════════════════════════════════════════════════════════════════════


class TestRedisBackend:
    """Tests for the RedisBackend.

    These tests require a running Redis instance. They are skipped
    gracefully if Redis is unavailable or redis-py is not installed.
    """

    @pytest.fixture(autouse=True)
    def _check_redis(self):
        try:
            import redis
            client = redis.Redis(host="localhost", port=6379, socket_connect_timeout=2)
            client.ping()
            self.backend = RedisBackend(host="localhost", port=6379, prefix="test_qna:")
        except Exception:
            pytest.skip("Redis not available — skipping RedisBackend tests")

    def teardown_method(self):
        if hasattr(self, "backend"):
            try:
                # Clean up test keys
                for key in self.backend.keys():
                    self.backend.delete(key)
                self.backend.close()
            except Exception:
                pass

    def test_set_and_get(self):
        self.backend.set("test_key", "test_value")
        assert self.backend.get("test_key") == "test_value"

    def test_get_nonexistent(self):
        assert self.backend.get("nonexistent") is None

    def test_set_various_types(self):
        self.backend.set("int_val", 42)
        self.backend.set("float_val", 3.14)
        self.backend.set("list_val", [1, 2, 3])
        self.backend.set("dict_val", {"nested": "data"})

        assert self.backend.get("int_val") == 42
        assert self.backend.get("float_val") == 3.14
        assert self.backend.get("list_val") == [1, 2, 3]
        assert self.backend.get("dict_val") == {"nested": "data"}

    def test_overwrite(self):
        self.backend.set("key", "first")
        self.backend.set("key", "second")
        assert self.backend.get("key") == "second"

    def test_delete(self):
        self.backend.set("key", "value")
        assert self.backend.delete("key") is True
        assert self.backend.get("key") is None

    def test_exists(self):
        self.backend.set("key", "value")
        assert self.backend.exists("key") is True
        assert self.backend.exists("nonexistent") is False

    def test_keys(self):
        self.backend.set("alpha", 1)
        self.backend.set("beta", 2)
        keys = self.backend.keys("alpha")
        assert "alpha" in keys

    def test_ttl(self):
        self.backend.set("ttl_key", "value", ttl=2)
        assert self.backend.get("ttl_key") == "value"
        # Don't wait for expiry — just verify it was set

    def test_health_check(self):
        health = self.backend.health_check()
        assert health["healthy"] is True
        assert health["backend"] == "RedisBackend"

    def test_import_error(self):
        """Test that ImportError is raised when redis is not available."""
        with patch.dict("sys.modules", {"redis": None}):
            with pytest.raises(ImportError, match="redis-py"):
                RedisBackend()


# ═══════════════════════════════════════════════════════════════════════════
# Factory Function Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestGetPersistenceBackend:
    """Tests for the get_persistence_backend factory function."""

    def test_memory_backend_explicit(self):
        backend = get_persistence_backend("memory")
        assert isinstance(backend, MemoryBackend)

    def test_file_backend_explicit(self):
        tmpdir = tempfile.mkdtemp()
        try:
            backend = get_persistence_backend("file", data_dir=tmpdir)
            assert isinstance(backend, FileBackend)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_env_var_memory(self):
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "memory"}):
            backend = get_persistence_backend()
            assert isinstance(backend, MemoryBackend)

    def test_env_var_file(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "file"}):
                backend = get_persistence_backend(data_dir=tmpdir)
                assert isinstance(backend, FileBackend)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_default_is_file(self):
        tmpdir = tempfile.mkdtemp()
        try:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("PERSISTENCE_BACKEND", None)
                backend = get_persistence_backend(data_dir=tmpdir)
                assert isinstance(backend, FileBackend)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_redis_fallback_to_file(self):
        """When Redis is requested but unavailable, fall back to FileBackend."""
        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "redis", "REDIS_HOST": "nonexistent.invalid"}):
            backend = get_persistence_backend()
            assert isinstance(backend, FileBackend)

    def test_unknown_backend_falls_back(self):
        backend = get_persistence_backend("unknown_backend")
        assert isinstance(backend, FileBackend)


# ═══════════════════════════════════════════════════════════════════════════
# RiskManager Persistence Integration Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestRiskManagerPersistence:
    """Tests that RiskManager correctly persists and loads state."""

    def test_persistence_on_update_pnl(self):
        """RiskManager should persist state when update_pnl is called."""
        from quant_nanggroe.engine.risk.manager import RiskManager

        backend = MemoryBackend()
        rm = RiskManager(initial_equity=1_000_000, persistence=backend)

        rm.update_pnl(-500.0)

        assert backend.get("risk:daily_pnl") == -500.0
        assert backend.get("risk:weekly_pnl") == -500.0
        assert backend.get("risk:trade_count_today") == 1
        assert backend.get("risk:current_equity") == 999_500.0

    def test_state_survives_restart(self):
        """RiskManager state should survive across instances."""
        from quant_nanggroe.engine.risk.manager import RiskManager

        backend = MemoryBackend()

        # First instance — accumulate some P&L
        rm1 = RiskManager(initial_equity=1_000_000, persistence=backend)
        rm1.update_pnl(-1000.0)
        rm1.update_pnl(-500.0)

        # Second instance — should load persisted state
        rm2 = RiskManager(initial_equity=1_000_000, persistence=backend)

        assert rm2.state.daily_pnl == -1500.0
        assert rm2.state.weekly_pnl == -1500.0
        assert rm2.state.trade_count_today == 2
        assert rm2.state.current_equity == 998_500.0

    def test_kill_switch_state_persisted(self):
        """Kill switch activation should be persisted and restored."""
        from quant_nanggroe.engine.risk.manager import RiskManager

        backend = MemoryBackend()

        rm1 = RiskManager(initial_equity=1_000_000, persistence=backend)
        rm1.kill_switch.activate("MANUAL_TEST")
        rm1._save_state()  # Explicitly persist after manual activation

        # Create new instance — should load kill switch state
        rm2 = RiskManager(initial_equity=1_000_000, persistence=backend)
        assert rm2.kill_switch.is_active is True

    def test_file_backend_integration(self):
        """Test RiskManager with FileBackend."""
        from quant_nanggroe.engine.risk.manager import RiskManager

        tmpdir = tempfile.mkdtemp()
        try:
            backend = FileBackend(data_dir=tmpdir)

            rm1 = RiskManager(initial_equity=1_000_000, persistence=backend)
            rm1.update_pnl(-200.0)

            # New instance with same FileBackend
            rm2 = RiskManager(initial_equity=1_000_000, persistence=backend)
            assert rm2.state.daily_pnl == -200.0
            assert rm2.state.trade_count_today == 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_no_persistence_arg_uses_default(self):
        """RiskManager without explicit persistence should use env-configured backend."""
        from quant_nanggroe.engine.risk.manager import RiskManager

        with patch.dict(os.environ, {"PERSISTENCE_BACKEND": "memory"}):
            rm = RiskManager(initial_equity=1_000_000)
            assert isinstance(rm._persistence, MemoryBackend)

    def test_persistence_preserves_equity_tracking(self):
        """Peak equity should be correctly persisted and restored."""
        from quant_nanggroe.engine.risk.manager import RiskManager

        backend = MemoryBackend()

        rm1 = RiskManager(initial_equity=1_000_000, persistence=backend)
        rm1.update_pnl(5000.0)  # Equity goes up to 1_005_000

        rm2 = RiskManager(initial_equity=1_000_000, persistence=backend)
        assert rm2.state.peak_equity == 1_005_000.0
        assert rm2.state.current_equity == 1_005_000.0

    def test_veto_and_approval_counts_persisted(self):
        """Veto and approval counts should survive restarts."""
        from quant_nanggroe.engine.risk.manager import RiskManager

        backend = MemoryBackend()

        rm1 = RiskManager(initial_equity=1_000_000, persistence=backend)
        rm1._veto_count = 5
        rm1._approval_count = 10
        rm1._save_state()

        rm2 = RiskManager(initial_equity=1_000_000, persistence=backend)
        assert rm2._veto_count == 5
        assert rm2._approval_count == 10
