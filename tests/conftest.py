"""
Pytest Configuration — Shared Fixtures for Quant-Nanggroe-AI Test Suite
========================================================================

Extended with additional fixtures for comprehensive testing.
"""

from __future__ import annotations

import os
import tempfile
from typing import Generator

import numpy as np
import pandas as pd
import pytest

# Set test environment BEFORE importing app modules — must match config.py
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_qna.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("QNAI_LOG_LEVEL", "WARNING")  # Reduce noise in tests


# ── Price Series Fixtures ──────────────────────────────────────────────


@pytest.fixture
def sample_closes() -> list[float]:
    """100-bar sample close price series for indicator testing."""
    np.random.seed(42)
    # Generate a realistic price series with trend + noise
    returns = np.random.normal(0.0002, 0.015, 100)
    prices = 100.0 * np.cumprod(1 + returns)
    return [round(float(p), 2) for p in prices]


@pytest.fixture
def sample_ohlcv() -> dict[str, list[float]]:
    """100-bar OHLCV sample data."""
    np.random.seed(42)
    returns = np.random.normal(0.0002, 0.015, 100)
    closes = 100.0 * np.cumprod(1 + returns)

    highs = [round(float(c) * (1 + abs(float(np.random.normal(0, 0.005)))), 2) for c in closes]
    lows = [round(float(c) * (1 - abs(float(np.random.normal(0, 0.005)))), 2) for c in closes]
    volumes = [round(float(max(np.random.lognormal(15, 1), 1000)), 0) for _ in range(100)]

    return {
        "opens": [round(float(c) * (1 + float(np.random.normal(0, 0.002))), 2) for c in closes],
        "highs": highs,
        "lows": lows,
        "closes": [round(float(c), 2) for c in closes],
        "volumes": volumes,
    }


@pytest.fixture
def rsi_overbought_closes() -> list[float]:
    """Price series that should produce RSI > 70 (overbought)."""
    return [100.0 + i * 0.5 for i in range(30)]


@pytest.fixture
def rsi_oversold_closes() -> list[float]:
    """Price series that should produce RSI < 30 (oversold)."""
    return [100.0 - i * 0.5 for i in range(30)]


@pytest.fixture
def trending_up_closes() -> list[float]:
    """Strong uptrend price series."""
    return [100.0 + i * 2.0 for i in range(50)]


@pytest.fixture
def ranging_closes() -> list[float]:
    """Sideways/ranging price series."""
    import math
    return [100.0 + 5.0 * math.sin(i * 0.2) for i in range(50)]


@pytest.fixture
def sample_portfolio_state() -> dict:
    """Sample portfolio state for risk management tests."""
    return {
        "total_equity": 100000.0,
        "cash": 60000.0,
        "positions": {
            "AAPL": {"quantity": 50, "entry_price": 180.0, "current_price": 185.0},
            "MSFT": {"quantity": 30, "entry_price": 380.0, "current_price": 375.0},
            "GOOGL": {"quantity": 20, "entry_price": 140.0, "current_price": 145.0},
        },
        "daily_pnl": -150.0,
        "weekly_pnl": 1200.0,
        "max_drawdown_pct": 2.1,
    }


# ── Engine Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def risk_guard():
    """ConstitutionalRiskGuard instance for testing."""
    from quant_nanggroe.engine.risk.checks import RiskCheckGate
    return RiskCheckGate()


@pytest.fixture
def kill_switch():
    """KillSwitch instance for testing."""
    from quant_nanggroe.engine.risk.kill_switch import KillSwitch
    return KillSwitch()


@pytest.fixture
def risk_manager():
    """RiskManager instance for testing."""
    from quant_nanggroe.engine.risk.manager import RiskManager
    return RiskManager(initial_equity=1_000_000.0)


@pytest.fixture
def drawdown_monitor():
    """DrawdownMonitor instance for testing."""
    from quant_nanggroe.engine.risk.drawdown import DrawdownMonitor
    return DrawdownMonitor(max_drawdown=0.10, initial_equity=1_000_000.0)


@pytest.fixture
def var_calculator():
    """VaRCalculator instance for testing."""
    from quant_nanggroe.engine.risk.var import VaRCalculator
    return VaRCalculator(default_confidence=0.95)


@pytest.fixture
def kelly_criterion():
    """KellyCriterion instance for testing."""
    from quant_nanggroe.engine.risk.kelly import KellyCriterion
    return KellyCriterion(max_position=0.20, min_position=0.01)


@pytest.fixture
def correlation_monitor():
    """CorrelationMonitor instance for testing."""
    from quant_nanggroe.engine.risk.correlation import CorrelationMonitor
    return CorrelationMonitor()


# ── Return Data Fixtures ───────────────────────────────────────────────


@pytest.fixture
def normal_returns():
    """1000 normal-distribution returns for VaR/risk testing."""
    np.random.seed(42)
    return np.random.normal(0.0001, 0.02, 1000)


@pytest.fixture
def ohlcv_df():
    """Standard 100-bar OHLCV DataFrame for factor testing."""
    np.random.seed(42)
    n = 100
    returns = np.random.normal(0.0002, 0.015, n)
    closes = 100.0 * np.cumprod(1 + returns)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")

    return pd.DataFrame({
        "open": closes * (1 + np.random.normal(0, 0.002, n)),
        "high": closes * (1 + np.abs(np.random.normal(0, 0.005, n))),
        "low": closes * (1 - np.abs(np.random.normal(0, 0.005, n))),
        "close": closes,
        "volume": np.maximum(np.random.lognormal(15, 1, n), 1000),
    }, index=dates)


# ── Persistence Fixtures ───────────────────────────────────────────────


@pytest.fixture
def tmp_persist_dir():
    """Temporary directory for persistence tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ── Agent State Fixtures ───────────────────────────────────────────────


@pytest.fixture
def initial_agent_state():
    """Initial AgentState for graph/routing tests."""
    from quant_nanggroe.agents.state import create_initial_state
    return create_initial_state(["BTC/USDT", "ETH/USDT"], "2024-01-15")


@pytest.fixture
def good_kelly_params():
    """Kelly parameters with a clear positive edge."""
    from quant_nanggroe.engine.risk.kelly import KellyParameters
    return KellyParameters(win_rate=0.6, avg_win=200.0, avg_loss=100.0, confidence=0.8)
