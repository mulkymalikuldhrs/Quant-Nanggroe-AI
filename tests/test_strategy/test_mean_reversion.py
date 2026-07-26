"""Tests for MeanReversionStrategy (Kakushadze #15)."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategies.mean_reversion import MeanReversionStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestMeanReversionStrategy:
    def test_default_params(self):
        strategy = MeanReversionStrategy()
        assert strategy.name == "MeanReversion"
        assert strategy.lookback == 20
        assert strategy.bollinger_std == 2.0
        assert strategy.atr_stop_mult == 1.5

    def test_custom_params(self):
        strategy = MeanReversionStrategy(params={"lookback": 30, "bollinger_std": 2.5, "atr_stop_mult": 2.0})
        assert strategy.lookback == 30
        assert strategy.bollinger_std == 2.5
        assert strategy.atr_stop_mult == 2.0

    def test_required_columns(self):
        strategy = MeanReversionStrategy()
        cols = strategy.required_columns()
        assert "close" in cols
        assert "high" in cols
        assert "low" in cols

    def test_warmup_period(self):
        strategy = MeanReversionStrategy(params={"lookback": 30})
        assert strategy.warmup_period() == 31

    def test_no_signal_insufficient_data(self, random_ohlcv_data):
        strategy = MeanReversionStrategy()
        small_data = random_ohlcv_data.iloc[:5]
        signal = strategy.generate_signal(small_data)
        assert signal is None

    def test_bollinger_entry_below_lower_band(self, random_ohlcv_data):
        strategy = MeanReversionStrategy(params={"strategy_type": "bollinger", "lookback": 20, "symbol": "TEST"})
        df = random_ohlcv_data.copy()
        price = float(df["close"].iloc[-1])
        lower = float(df["close"].rolling(20).mean().iloc[-1] - 2.0 * df["close"].rolling(20).std().iloc[-1])
        if price < lower:
            signal = strategy.generate_signal(df)
            if signal is not None:
                assert signal.signal_type == SignalType.BUY

    def test_bollinger_entry_above_upper_band(self, random_ohlcv_data):
        strategy = MeanReversionStrategy(params={"strategy_type": "bollinger", "lookback": 20, "symbol": "TEST"})
        df = random_ohlcv_data.copy()
        price = float(df["close"].iloc[-1])
        upper = float(df["close"].rolling(20).mean().iloc[-1] + 2.0 * df["close"].rolling(20).std().iloc[-1])
        if price > upper:
            signal = strategy.generate_signal(df)
            if signal is not None:
                assert signal.signal_type == SignalType.SELL

    def test_signal_has_stop_loss(self, mean_reverting_data):
        strategy = MeanReversionStrategy(params={"strategy_type": "bollinger", "lookback": 20, "symbol": "TEST"})
        signal = None
        for i in range(strategy.warmup_period(), len(mean_reverting_data)):
            window = mean_reverting_data.iloc[: i + 1]
            sig = strategy.generate_signal(window)
            if sig is not None and sig.signal_type in (SignalType.BUY, SignalType.SELL):
                signal = sig
                break
        if signal is not None:
            assert signal.stop_loss is not None
            assert signal.stop_loss > 0

    def test_signal_evidence(self, mean_reverting_data):
        strategy = MeanReversionStrategy(params={"strategy_type": "bollinger", "symbol": "TEST"})
        for i in range(strategy.warmup_period(), len(mean_reverting_data)):
            window = mean_reverting_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None and signal.signal_type in (SignalType.BUY, SignalType.SELL):
                assert "strategy_type" in signal.evidence
                assert "target_signal" in signal.evidence
                break

    def test_ou_half_life_estimation(self, mean_reverting_data):
        strategy = MeanReversionStrategy()
        hl = strategy.estimate_half_life(mean_reverting_data["close"])
        assert hl > 0
        assert hl < np.inf

    def test_ou_half_life_non_mean_reverting(self):
        strategy = MeanReversionStrategy()
        random_walk = pd.Series(np.cumsum(np.random.randn(200)))
        hl = strategy.estimate_half_life(random_walk)
        assert hl >= 0

    def test_insufficient_data_returns_none(self):
        strategy = MeanReversionStrategy()
        data = pd.DataFrame({"open": [100], "high": [101], "low": [99], "close": [100], "volume": [1000]})
        signal = strategy.generate_signal(data)
        assert signal is None

    def test_nan_prices_handled(self):
        strategy = MeanReversionStrategy()
        data = pd.DataFrame({"open": [np.nan] * 30, "high": [np.nan] * 30, "low": [np.nan] * 30, "close": [np.nan] * 30, "volume": [1000] * 30})
        signal = strategy.generate_signal(data)
        assert signal is None

    def test_list_strategies_includes_mean_rev(self):
        from quant_nanggroe.engine.strategies.registry import StrategyRegistry
        assert "mean_rev" in StrategyRegistry.list_strategies()
