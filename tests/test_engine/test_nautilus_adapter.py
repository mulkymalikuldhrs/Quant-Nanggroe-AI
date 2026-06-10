"""Tests for NautilusTrader adapter module."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe_ai.engine.nautilus_adapter import (
    BacktestConfig,
    NautilusAdapter,
    NautilusResults,
    is_nautilus_available,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "open": close + np.random.randn(n) * 0.2,
        "high": close + abs(np.random.randn(n) * 0.3),
        "low": close - abs(np.random.randn(n) * 0.3),
        "close": close,
        "volume": np.random.randint(1000, 100000, n).astype(float),
    }, index=dates)


@pytest.fixture
def backtest_config() -> BacktestConfig:
    """Create a test backtest configuration."""
    return BacktestConfig(
        symbols=["TEST"],
        timeframe="1-HOUR",
        start_date="2024-01-01",
        end_date="2024-06-30",
    )


# ── Availability ──────────────────────────────────────────────────────────

class TestNautilusAvailability:
    def test_is_nautilus_available_returns_bool(self):
        result = is_nautilus_available()
        assert isinstance(result, bool)

    def test_nautilus_not_installed_in_test_env(self):
        assert is_nautilus_available() is False


# ── BacktestConfig ────────────────────────────────────────────────────────

class TestBacktestConfig:
    def test_create_config(self):
        config = BacktestConfig(symbols=["AAPL"])
        assert config.symbols == ["AAPL"]
        assert config.initial_capital == 100000.0

    def test_config_defaults(self):
        config = BacktestConfig(symbols=["AAPL"])
        assert config.leverage == 1
        assert config.commission == 0.0002
        assert config.slippage == 0.0


# ── NautilusResults ───────────────────────────────────────────────────────

class TestNautilusResults:
    def test_create_results(self):
        results = NautilusResults(
            total_return=0.15,
            sharpe_ratio=1.5,
            max_drawdown=-0.08,
            win_rate=0.55,
            total_trades=100,
        )
        assert results.total_return == 0.15
        assert results.sharpe_ratio == 1.5
        assert results.total_trades == 100

    def test_to_backtest_result_compatible(self):
        results = NautilusResults(
            total_return=0.10,
            sharpe_ratio=1.2,
            max_drawdown=-0.05,
            win_rate=0.6,
            total_trades=50,
        )
        compat = results.to_backtest_result_compatible()
        assert isinstance(compat, dict)
        assert "total_return" in compat


# ── NautilusAdapter ───────────────────────────────────────────────────────

class TestNautilusAdapter:
    def test_create_adapter(self):
        adapter = NautilusAdapter()
        assert adapter is not None

    def test_adapter_status_without_nautilus(self):
        adapter = NautilusAdapter()
        status = adapter.status()
        assert isinstance(status, dict)
        assert "nautilus_available" in status
