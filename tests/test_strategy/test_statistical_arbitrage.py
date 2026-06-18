"""Tests for StatisticalArbitrageStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.strategies.statistical_arbitrage import (
    StatisticalArbitrageStrategy,
)
from quant_nanggroe.types.signals import Signal, SignalType


class TestStatisticalArbitrageStrategy:
    """Test statistical arbitrage strategy."""

    def test_default_params(self):
        strategy = StatisticalArbitrageStrategy()
        assert strategy.name == "StatisticalArbitrage"
        assert strategy.n_factors == 3
        assert strategy.entry_z == 2.0

    def test_required_columns(self):
        strategy = StatisticalArbitrageStrategy()
        assert "close" in strategy.required_columns()

    def test_warmup_period(self):
        strategy = StatisticalArbitrageStrategy(params={"lookback": 50})
        assert strategy.warmup_period() == 80

    def test_generate_signal(self, random_ohlcv_data):
        strategy = StatisticalArbitrageStrategy(
            params={"entry_z": 1.5, "symbol": "TEST"}
        )
        signal = strategy.generate_signal(random_ohlcv_data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [
                SignalType.BUY, SignalType.SELL,
                SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT,
            ]

    def test_residual_zscore(self):
        strategy = StatisticalArbitrageStrategy()
        residuals = np.random.randn(100) * 0.01
        z_scores = strategy.compute_residual_zscore(residuals, 20)
        assert len(z_scores) == 100
        # Some should be NaN (warmup period)
        assert np.isnan(z_scores[0])

    def test_half_life_estimation(self):
        strategy = StatisticalArbitrageStrategy()
        # Mean-reverting residuals
        residuals = np.sin(np.linspace(0, 20 * np.pi, 200)) * 0.01
        hl = strategy.estimate_half_life(residuals)
        assert hl > 0

    def test_kalman_exposure(self):
        strategy = StatisticalArbitrageStrategy()
        n = 100
        asset_returns = np.random.randn(n) * 0.02
        factor_returns = np.random.randn(n, 3) * 0.01
        exposures = strategy.compute_kalman_exposure(asset_returns, factor_returns)
        assert exposures.shape == (n, 3)

    def test_with_kalman_disabled(self, random_ohlcv_data):
        strategy = StatisticalArbitrageStrategy(
            params={"use_kalman": False, "entry_z": 1.5, "symbol": "TEST"}
        )
        signal = strategy.generate_signal(random_ohlcv_data)
        if signal is not None:
            assert isinstance(signal, Signal)

    def test_insufficient_data(self):
        strategy = StatisticalArbitrageStrategy()
        data = pd.DataFrame({"close": [100, 101, 102]})
        signal = strategy.generate_signal(data)
        assert signal is None

    def test_signal_evidence(self, random_ohlcv_data):
        strategy = StatisticalArbitrageStrategy(
            params={"entry_z": 1.0, "symbol": "TEST"}
        )
        # Run on multiple windows
        for i in range(strategy.warmup_period(), len(random_ohlcv_data)):
            window = random_ohlcv_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None and signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                assert "residual_z" in signal.evidence
                assert "n_factors" in signal.evidence
                break
