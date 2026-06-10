"""
Pytest Configuration — Shared Fixtures for Quant-Nanggroe-AI Test Suite
========================================================================
"""

from __future__ import annotations

import os
from typing import Generator

import pytest
import numpy as np

# Set test environment BEFORE importing app modules — must match config.py
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_qna.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")


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
    from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard
    return ConstitutionalRiskGuard()


@pytest.fixture
def market_engine():
    """MarketStateEngine instance for testing."""
    from quant_nanggroe_ai.engine.market_state import MarketStateEngine
    return MarketStateEngine()


@pytest.fixture
def kill_switch(tmp_path):
    """KillSwitch instance with isolated temp directory for state persistence."""
    from quant_nanggroe_ai.engine.kill_switch import KillSwitch
    return KillSwitch(state_dir=str(tmp_path))
