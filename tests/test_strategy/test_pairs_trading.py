"""Tests for PairsTradingStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.strategies.pairs_trading import PairsTradingStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestPairsTradingStrategy:
    """Test pairs trading strategy."""

    def test_default_params(self):
        strategy = PairsTradingStrategy()
        assert strategy.name == "PairsTrading"
        assert strategy.lookback == 60
        assert strategy.entry_z == 2.0
        assert strategy.coint_method == "engle_granger"

    def test_required_columns(self):
        strategy = PairsTradingStrategy()
        assert "close_y" in strategy.required_columns()
        assert "close_x" in strategy.required_columns()

    def test_warmup_period(self):
        strategy = PairsTradingStrategy(params={"lookback": 50})
        assert strategy.warmup_period() == 80  # lookback + 30

    def test_engle_granger_cointegration(self, cointegrated_pair_data):
        strategy = PairsTradingStrategy()
        y = cointegrated_pair_data["close_y"]
        x = cointegrated_pair_data["close_x"]
        score, pvalue = strategy.test_cointegration_engle_granger(y, x)
        # Cointegrated data should have low p-value
        assert isinstance(pvalue, float)
        assert 0 <= pvalue <= 1

    def test_johansen_cointegration(self, cointegrated_pair_data):
        strategy = PairsTradingStrategy()
        y = cointegrated_pair_data["close_y"]
        x = cointegrated_pair_data["close_x"]
        stat, pvalue = strategy.test_cointegration_johansen(y, x)
        assert isinstance(pvalue, float)

    def test_ols_hedge_ratio(self, cointegrated_pair_data):
        strategy = PairsTradingStrategy()
        y = cointegrated_pair_data["close_y"]
        x = cointegrated_pair_data["close_x"]
        hedge_ratio, residuals = strategy.compute_hedge_ratio_ols(y, x)
        # Should be close to 2.0 (the generating coefficient)
        assert abs(hedge_ratio - 2.0) < 0.5

    def test_kalman_hedge_ratio(self, cointegrated_pair_data):
        strategy = PairsTradingStrategy()
        y = cointegrated_pair_data["close_y"]
        x = cointegrated_pair_data["close_x"]
        hedge_ratios, residuals = strategy.compute_hedge_ratio_kalman(y, x)
        assert len(hedge_ratios) == len(y)
        # Kalman should converge to approximately 2.0
        assert abs(hedge_ratios.iloc[-1] - 2.0) < 1.0

    def test_spread_computation(self):
        strategy = PairsTradingStrategy()
        y = pd.Series([10, 11, 12, 13, 14], dtype=float)
        x = pd.Series([5, 5.5, 6, 6.5, 7], dtype=float)
        spread = strategy.compute_spread(y, x, 2.0)
        expected = y - 2.0 * x
        pd.testing.assert_series_equal(spread, expected)

    def test_half_life_estimation(self):
        strategy = PairsTradingStrategy()
        # Mean-reverting series
        spread = pd.Series(np.sin(np.linspace(0, 10 * np.pi, 100)) + np.random.randn(100) * 0.1)
        hl = strategy.estimate_half_life(spread)
        assert hl > 0

    def test_generate_signal_cointegrated(self, cointegrated_pair_data):
        strategy = PairsTradingStrategy(
            params={"entry_z": 1.5, "exit_z": 0.5, "symbol_y": "Y", "symbol_x": "X"}
        )
        signals = []
        for i in range(strategy.warmup_period(), len(cointegrated_pair_data)):
            window = cointegrated_pair_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None:
                signals.append(signal)

        for sig in signals:
            assert isinstance(sig, Signal)
            assert sig.signal_type in [
                SignalType.BUY, SignalType.SELL,
                SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT,
            ]

    def test_signal_evidence(self, cointegrated_pair_data):
        strategy = PairsTradingStrategy(
            params={"entry_z": 1.0, "symbol_y": "Y", "symbol_x": "X"}
        )
        for i in range(strategy.warmup_period(), len(cointegrated_pair_data)):
            window = cointegrated_pair_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None and signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                assert "spread_z" in signal.evidence
                assert "hedge_ratio" in signal.evidence
                assert "coint_pvalue" in signal.evidence
                break

    def test_insufficient_data(self):
        strategy = PairsTradingStrategy()
        small_data = pd.DataFrame({
            "close_y": [1, 2, 3],
            "close_x": [1, 2, 3],
        })
        signal = strategy.generate_signal(small_data)
        assert signal is None

    def test_kalman_method(self, cointegrated_pair_data):
        strategy = PairsTradingStrategy(
            params={"hedge_method": "kalman", "entry_z": 1.5}
        )
        signal = strategy.generate_signal(cointegrated_pair_data)
        # May or may not produce a signal, but should not error
        if signal is not None:
            assert isinstance(signal, Signal)
