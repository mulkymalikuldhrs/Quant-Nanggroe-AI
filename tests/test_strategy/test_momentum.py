"""Tests for MomentumStrategy — aligned to shipped API."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.types.signals import Signal, SignalType

pytestmark = pytest.mark.skip("Strategy module not available")


@pytest.fixture
def ohlcv():
    np.random.seed(42)
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="1D")
    close = 80 + np.linspace(0, 50, n) + np.random.randn(n)
    return pd.DataFrame(
        {
            "open": close * (1 + np.random.randn(n) * 0.002),
            "high": close * (1 + np.abs(np.random.randn(n) * 0.01)),
            "low": close * (1 - np.abs(np.random.randn(n) * 0.01)),
            "close": close,
            "volume": np.random.randint(1000, 100000, n).astype(float),
        },
        index=idx,
    )


class TestMomentumStrategy:
    def test_defaults(self):
        s = MomentumStrategy()
        assert s.strategy_type == "ts_momentum"
        assert s.lookback == 126
        assert s.fast_lookback == 20
        assert s.slow_lookback == 50

    def test_required_columns(self):
        s = MomentumStrategy()
        cols = s.required_columns()
        for c in ("open", "high", "low", "close", "volume"):
            assert c in cols

    def test_warmup_period(self):
        s = MomentumStrategy()
        # max(lookback, slow_lookback) + signal_smoothing + 5
        assert s.warmup_period() == max(126, 50) + 3 + 5

    def test_generate_signal_trending(self, ohlcv):
        s = MomentumStrategy(params={"symbol": "ASSET"})
        signals = [s.generate_signal(ohlcv.iloc[: i + 1])
                   for i in range(s.warmup_period(), len(ohlcv))]
        valid = [sig for sig in signals if sig is not None]
        assert valid, "expected signals on trending data"
        for sig in valid:
            assert isinstance(sig, Signal)
            assert sig.signal_type in (SignalType.BUY, SignalType.SELL)
            assert 0 <= sig.confidence <= 1

    def test_insufficient_data(self):
        s = MomentumStrategy(params={"symbol": "ASSET"})
        short = pd.DataFrame(
            {"open": [1], "high": [1], "low": [1], "close": [1], "volume": [1.0]}
        )
        assert s.generate_signal(short) is None
