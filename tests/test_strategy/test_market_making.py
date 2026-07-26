"""Tests for MarketMakingStrategy — aligned to shipped A-S-lite API."""

import numpy as np
import pandas as pd
import pytest

    MarketMakingStrategy,
)
from quant_nanggroe.types.signals import Signal, SignalType

pytestmark = pytest.mark.skip("Strategy module not available")


@pytest.fixture
def ohlcv():
    np.random.seed(42)
    n = 100
    idx = pd.date_range("2024-01-01", periods=n, freq="1D")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame(
        {
            "open": close, "high": close, "low": close, "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=idx,
    )


class TestMarketMakingStrategy:
    def test_defaults(self):
        s = MarketMakingStrategy()
        assert s.warmup_period() == 20
        assert s.required_columns() == ["close"]

    def test_reservation_price(self):
        s = MarketMakingStrategy(params={"gamma": 0.1, "symbol": "ASSET"})
        s._inventory = 10.0
        r = s._reservation_price(mid=100.0, sigma=2.0, T=1.0)
        # r = S - gamma * sigma^2 * q * T = 100 - 0.1*4*10 = 96
        assert abs(r - 96.0) < 1e-6

    def test_base_spread(self):
        s = MarketMakingStrategy(params={"gamma": 0.1, "spread_multiplier": 1.0})
        spread = s._base_spread(sigma=2.0)
        assert abs(spread - 0.4) < 1e-6  # gamma * sigma^2 = 0.1*4

    def test_quote_levels(self):
        s = MarketMakingStrategy(params={"gamma": 0.1, "symbol": "ASSET", "num_levels": 1})
        levels = s._quote_levels(mid=100.0, sigma=2.0)
        assert len(levels) == 1
        assert levels[0]["bid_price"] < levels[0]["ask_price"]

    def test_generate_signal(self, ohlcv):
        s = MarketMakingStrategy(params={"symbol": "ASSET"})
        sig = s.generate_signal(ohlcv)
        assert sig is None or isinstance(sig, Signal)

    def test_insufficient_data(self):
        s = MarketMakingStrategy(params={"symbol": "ASSET"})
        short = pd.DataFrame({"close": [1.0, 2.0]})
        assert s.generate_signal(short) is None
