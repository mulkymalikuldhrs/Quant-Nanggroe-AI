"""Tests for PairsTradingStrategy — aligned to shipped (simplified) API.

The strategy uses OLS hedge ratio via lstsq (no statsmodels) and reads
two-leg columns named by `symbol` / `symbol_pair` params.
"""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.types.signals import Signal, SignalType


@pytest.fixture
def pair_data():
    np.random.seed(42)
    n = 250
    idx = pd.date_range("2024-01-01", periods=n, freq="1D")
    x = 100 + np.cumsum(np.random.randn(n) * 0.5)
    spread = np.zeros(n)
    spread[0] = 0.5
    for t in range(1, n):
        spread[t] = 0.8 * spread[t - 1] + np.random.randn() * 0.3
    y = 2.0 * x + spread
    return pd.DataFrame({"ASSET_A": x, "ASSET_B": y}, index=idx)


class TestPairsTradingStrategy:
    def test_default_lookback(self):
        s = PairsTradingStrategy(params={"symbol": "ASSET_A", "symbol_pair": "ASSET_B"})
        assert s.lookback == 60
        assert s.entry_z == 2.0

    def test_required_columns(self):
        s = PairsTradingStrategy(params={"symbol": "ASSET_A", "symbol_pair": "ASSET_B"})
        cols = s.required_columns()
        assert "ASSET_A" in cols and "ASSET_B" in cols

    def test_warmup_period(self):
        s = PairsTradingStrategy(
            params={"symbol": "ASSET_A", "symbol_pair": "ASSET_B",
                    "lookback": 30, "hedge_ratio_lookback": 60}
        )
        assert s.warmup_period() == 90  # hedge_ratio_lookback + lookback

    def test_ols_hedge_ratio(self, pair_data):
        # ponytail: lstsq slope should be ≈ 2.0
        s = PairsTradingStrategy(params={"symbol": "ASSET_A", "symbol_pair": "ASSET_B"})
        hr = s._ols_hedge_ratio(pair_data["ASSET_B"], pair_data["ASSET_A"])
        assert abs(hr - 2.0) < 0.5

    def test_insufficient_data(self):
        s = PairsTradingStrategy(params={"symbol": "ASSET_A", "symbol_pair": "ASSET_B"})
        small = pd.DataFrame({"ASSET_A": [1, 2, 3], "ASSET_B": [2, 4, 6]})
        assert s.generate_signal(small) is None

    def test_generate_signal_cointegrated(self, pair_data):
        s = PairsTradingStrategy(
            params={"symbol": "ASSET_A", "symbol_pair": "ASSET_B",
                    "entry_z": 1.0, "exit_z": 0.3,
                    "lookback": 30, "hedge_ratio_lookback": 60}
        )
        signals = [s.generate_signal(pair_data.iloc[: i + 1])
                   for i in range(s.warmup_period(), len(pair_data))]
        valid = [sig for sig in signals if sig is not None]
        assert valid, "expected at least one signal on cointegrated data"
        for sig in valid:
            assert isinstance(sig, Signal)
            assert sig.signal_type in (SignalType.BUY, SignalType.SELL,
                                       SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT)

    def test_signal_evidence(self, pair_data):
        s = PairsTradingStrategy(
            params={"symbol": "ASSET_A", "symbol_pair": "ASSET_B",
                    "entry_z": 0.8, "lookback": 30, "hedge_ratio_lookback": 60}
        )
        for i in range(s.warmup_period(), len(pair_data)):
            sig = s.generate_signal(pair_data.iloc[: i + 1])
            if sig is not None and sig.signal_type in (SignalType.BUY, SignalType.SELL):
                assert "hedge_ratio" in sig.evidence
                assert "spread_z" in sig.evidence
                break
