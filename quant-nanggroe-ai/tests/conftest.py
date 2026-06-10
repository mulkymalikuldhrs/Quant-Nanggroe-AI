"""Shared pytest fixtures for Quant Nanggroe AI tests."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Generator

import numpy as np
import pytest

# Set test environment variables BEFORE importing settings
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("CACHE_BACKEND", "memory")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_data/test.db")


@pytest.fixture
def sample_closes() -> np.ndarray:
    """Generate sample closing price data (100 data points)."""
    np.random.seed(42)
    # Simulate a price series with trend and noise
    returns = np.random.normal(0.001, 0.02, 100)
    closes = 100.0 * np.cumprod(1 + returns)
    return closes


@pytest.fixture
def sample_ohlcv_data() -> dict[str, np.ndarray]:
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    n = 100

    returns = np.random.normal(0.001, 0.02, n)
    closes = 100.0 * np.cumprod(1 + returns)

    # Generate realistic highs and lows
    spread = np.random.uniform(0.001, 0.01, n)
    highs = closes * (1 + spread)
    lows = closes * (1 - spread)

    # Opens are between previous close and current close
    opens = np.zeros(n)
    opens[0] = 100.0
    for i in range(1, n):
        opens[i] = np.random.uniform(lows[i], highs[i])

    volumes = np.random.uniform(1000, 10000, n)

    return {
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "volumes": volumes,
    }


@pytest.fixture
def trending_closes() -> np.ndarray:
    """Generate a strongly trending price series."""
    np.random.seed(100)
    returns = np.random.normal(0.005, 0.01, 100)
    return 100.0 * np.cumprod(1 + returns)


@pytest.fixture
def crashing_closes() -> np.ndarray:
    """Generate a price series with a crash (for PANIC regime testing)."""
    np.random.seed(200)
    returns = np.random.normal(0.0, 0.01, 95)
    # Add a crash: -6% per candle for 5 candles
    crash = np.array([-0.06, -0.05, -0.07, -0.04, -0.06])
    returns = np.concatenate([returns, crash])
    return 100.0 * np.cumprod(1 + returns)


@pytest.fixture
def range_closes() -> np.ndarray:
    """Generate a range-bound price series."""
    np.random.seed(300)
    # Mean-reverting series
    returns = np.random.normal(0.0, 0.005, 100)
    return 100.0 * np.cumprod(1 + returns)
