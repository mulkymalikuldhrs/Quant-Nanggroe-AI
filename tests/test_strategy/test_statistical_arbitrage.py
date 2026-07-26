"""Tests for StatisticalArbitrageStrategy — aligned to shipped API.

Strategy runs PCA (via SVD, no sklearn) on a multi-column `close` DataFrame
and trades the primary symbol's residual z-score.
"""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategies.statistical_arbitrage import (
    StatisticalArbitrageStrategy,
)
from quant_nanggroe.types.signals import Signal, SignalType


@pytest.fixture
def universe_close():
    np.random.seed(42)
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="1D")
    uni = {f"STK{i}": 100 + np.cumsum(np.random.randn(n) * 0.5) for i in range(5)}
    U = pd.DataFrame(uni, index=idx)
    # ponytail: real contract — `close` is a MultiIndex column holding the universe frame
    cols = pd.MultiIndex.from_product([["close"], [f"STK{i}" for i in range(5)]])
    return pd.DataFrame(U.values, index=idx, columns=cols)


class TestStatisticalArbitrageStrategy:
    def test_defaults(self):
        s = StatisticalArbitrageStrategy()
        assert s.lookback == 60
        assert s.n_factors == 3
        assert s.entry_threshold == 2.0

    def test_required_columns(self):
        s = StatisticalArbitrageStrategy()
        assert s.required_columns() == ["close"]

    def test_warmup_period(self):
        s = StatisticalArbitrageStrategy()
        assert s.warmup_period() == max(60, 20) + 1

    def test_pca_shape(self):
        # ponytail: SVD-based PCA, no sklearn
        mat = np.random.randn(100, 5)
        factors, loadings = StatisticalArbitrageStrategy._compute_pca(mat, 3)
        assert factors.shape == (100, 3)
        assert loadings.shape == (5, 3)

    def test_generate_signal_universe(self, universe_close):
        s = StatisticalArbitrageStrategy(params={"symbol": "STK0", "entry_threshold": 3.0})
        signals = [s.generate_signal(universe_close.iloc[: i + 1])
                   for i in range(s.warmup_period(), len(universe_close))]
        # Should run without error; may or may not produce a signal
        for sig in signals:
            if sig is not None:
                assert isinstance(sig, Signal)
                assert sig.signal_type in (SignalType.BUY, SignalType.SELL,
                                           SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT,
                                           SignalType.EXIT_ALL)

    def test_insufficient_data(self):
        s = StatisticalArbitrageStrategy(params={"symbol": "STK0"})
        # ponytail: too-short MultiIndex close frame (1 row, 2 stocks)
        small = pd.DataFrame(
            [[1.0, 2.0]],
            columns=pd.MultiIndex.from_product([["close"], ["STK0", "STK1"]]),
        )
        assert s.generate_signal(small) is None
