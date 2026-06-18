"""Shared test fixtures for strategy tests."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def random_ohlcv_data():
    """Generate random OHLCV data for testing."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="1D")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    close = np.maximum(close, 10)  # Keep prices positive
    high = close * (1 + np.abs(np.random.randn(n) * 0.01))
    low = close * (1 - np.abs(np.random.randn(n) * 0.01))
    open_ = close * (1 + np.random.randn(n) * 0.005)
    volume = np.random.randint(1000, 100000, n).astype(float)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )
    return df


@pytest.fixture
def mean_reverting_data():
    """Generate mean-reverting price data for testing."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="1D")

    # OU process: dX = theta*(mu - X)*dt + sigma*dW
    theta = 0.1
    mu = 100.0
    sigma = 2.0
    dt = 1.0

    prices = np.zeros(n)
    prices[0] = mu
    for t in range(1, n):
        prices[t] = prices[t - 1] + theta * (mu - prices[t - 1]) * dt + sigma * np.random.randn() * np.sqrt(dt)

    high = prices * (1 + np.abs(np.random.randn(n) * 0.005))
    low = prices * (1 - np.abs(np.random.randn(n) * 0.005))
    open_ = prices * (1 + np.random.randn(n) * 0.002)
    volume = np.random.randint(1000, 100000, n).astype(float)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": prices,
            "volume": volume,
        },
        index=dates,
    )
    return df


@pytest.fixture
def trending_up_data():
    """Generate trending-up price data for testing."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="1D")
    trend = np.linspace(80, 130, n)
    noise = np.random.randn(n) * 1.0
    close = trend + noise
    high = close * (1 + np.abs(np.random.randn(n) * 0.005))
    low = close * (1 - np.abs(np.random.randn(n) * 0.005))
    open_ = close * (1 + np.random.randn(n) * 0.002)
    volume = np.random.randint(1000, 100000, n).astype(float)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )
    return df


@pytest.fixture
def cointegrated_pair_data():
    """Generate cointegrated pair data for testing."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="1D")

    # Generate cointegrated series: Y = 2*X + spread, where spread is mean-reverting
    x = 100 + np.cumsum(np.random.randn(n) * 0.5)
    spread = np.zeros(n)
    spread[0] = 0.5
    for t in range(1, n):
        spread[t] = 0.8 * spread[t - 1] + np.random.randn() * 0.3
    y = 2.0 * x + spread

    df = pd.DataFrame(
        {
            "close_y": y,
            "close_x": x,
        },
        index=dates,
    )
    return df


@pytest.fixture
def funding_rate_data():
    """Generate crypto data with funding rates."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="8h")

    close = 40000 + np.cumsum(np.random.randn(n) * 200)
    close = np.maximum(close, 30000)
    volume = np.random.randint(100, 10000, n).astype(float)

    # Funding rates: mostly around 0.01% with occasional spikes
    funding_rate = np.random.randn(n) * 0.0002 + 0.0001
    # Add some extreme values
    funding_rate[50] = 0.001
    funding_rate[100] = -0.0008
    funding_rate[150] = 0.0005

    df = pd.DataFrame(
        {
            "close": close,
            "volume": volume,
            "funding_rate": funding_rate,
        },
        index=dates,
    )
    return df
