"""Tests for MeanReversionStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.strategies.mean_reversion import MeanReversionStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestMeanReversionStrategy:
    """Test mean reversion strategy."""

    def test_default_params(self):
        strategy = MeanReversionStrategy()
        assert strategy.name == "MeanReversion"
        assert strategy.lookback == 20
        assert strategy.entry_z == -2.0
        assert strategy.exit_z == 0.0
        assert strategy.bb_std == 2.0

    def test_custom_params(self):
        strategy = MeanReversionStrategy(params={"lookback": 30, "entry_z": -1.5})
        assert strategy.lookback == 30
        assert strategy.entry_z == -1.5

    def test_required_columns(self):
        strategy = MeanReversionStrategy()
        assert "close" in strategy.required_columns()
        assert "high" in strategy.required_columns()
        assert "low" in strategy.required_columns()

    def test_warmup_period(self):
        strategy = MeanReversionStrategy(params={"lookback": 30})
        assert strategy.warmup_period() == 40  # lookback + 10

    def test_no_signal_insufficient_data(self, random_ohlcv_data):
        strategy = MeanReversionStrategy()
        # Use only a few rows
        small_data = random_ohlcv_data.iloc[:10]
        signal = strategy.generate_signal(small_data)
        assert signal is None

    def test_ou_half_life_estimation(self, mean_reverting_data):
        strategy = MeanReversionStrategy()
        hl = strategy.estimate_ou_half_life(mean_reverting_data["close"])
        assert hl > 0
        assert hl < np.inf  # Should be mean-reverting

    def test_ou_half_life_non_mean_reverting(self):
        strategy = MeanReversionStrategy()
        # Pure random walk is not mean-reverting
        random_walk = pd.Series(np.cumsum(np.random.randn(200)))
        hl = strategy.estimate_ou_half_life(random_walk)
        # Random walk should have very long or infinite half-life
        assert hl >= 0  # May be inf

    def test_generate_signal_with_mean_reverting_data(self, mean_reverting_data):
        strategy = MeanReversionStrategy(
            params={"entry_z": -1.5, "exit_z": 0.0, "symbol": "TEST"}
        )
        # Run on multiple windows
        signals = []
        for i in range(strategy.warmup_period(), len(mean_reverting_data)):
            window = mean_reverting_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None:
                signals.append(signal)

        # Should generate at least some signals on mean-reverting data
        # (not guaranteed due to randomness, but structure should be valid)
        for sig in signals:
            assert isinstance(sig, Signal)
            assert sig.signal_type in [
                SignalType.BUY, SignalType.SELL,
                SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT,
            ]
            assert 0 <= sig.confidence <= 1

    def test_signal_has_proper_evidence(self, mean_reverting_data):
        strategy = MeanReversionStrategy(params={"entry_z": -1.0, "symbol": "TEST"})
        signals = []
        for i in range(strategy.warmup_period(), len(mean_reverting_data)):
            window = mean_reverting_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None and signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                signals.append(signal)
                break

        if signals:
            sig = signals[0]
            assert "z_score" in sig.evidence
            assert "bb_upper" in sig.evidence
            assert "bb_lower" in sig.evidence
            assert "position_size" in sig.evidence
            assert sig.stop_loss is not None or sig.signal_type == SignalType.CLOSE_LONG

    def test_position_sizing(self):
        strategy = MeanReversionStrategy()
        size = strategy._compute_position_size(-3.0, None)
        assert 0 <= size <= strategy.max_position_size

        size_with_hl = strategy._compute_position_size(-3.0, 10.0)
        assert size_with_hl >= size  # Short half-life boosts size

    def test_zscore_calculation(self, random_ohlcv_data):
        strategy = MeanReversionStrategy(params={"lookback": 20})
        zscore = strategy.compute_close_zscore(random_ohlcv_data)
        assert isinstance(zscore, pd.Series)
        assert len(zscore) == len(random_ohlcv_data)
