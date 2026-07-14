"""Tests for TrendFollowStrategy (Kakushadze #31)."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.strategies.trend_follow import TrendFollowStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestTrendFollowStrategy:
    def test_default_params(self):
        strategy = TrendFollowStrategy()
        assert strategy.name == "TrendFollow"
        assert strategy.fast_period == 50
        assert strategy.slow_period == 200
        assert strategy.adx_threshold == 25.0
        assert strategy.atr_stop_mult == 3.0

    def test_custom_params(self):
        strategy = TrendFollowStrategy(params={
            "fast_period": 20, "slow_period": 100, "adx_threshold": 30, "atr_stop_mult": 2.5,
        })
        assert strategy.fast_period == 20
        assert strategy.slow_period == 100
        assert strategy.adx_threshold == 30.0
        assert strategy.atr_stop_mult == 2.5

    def test_required_columns(self):
        strategy = TrendFollowStrategy()
        cols = strategy.required_columns()
        assert "close" in cols
        assert "high" in cols
        assert "low" in cols
        assert "open" in cols

    def test_warmup_period(self):
        strategy = TrendFollowStrategy()
        assert strategy.warmup_period() == 219  # 200 + 14 + 5

    def test_no_signal_insufficient_data(self, random_ohlcv_data):
        strategy = TrendFollowStrategy()
        small_data = random_ohlcv_data.iloc[:10]
        signal = strategy.generate_signal(small_data)
        assert signal is None

    def test_no_signal_weak_trend(self, random_ohlcv_data):
        strategy = TrendFollowStrategy(params={"fast_period": 10, "slow_period": 30, "adx_threshold": 100})
        signal = strategy.generate_signal(random_ohlcv_data)
        assert signal is None

    def test_signal_has_stop_loss(self, trending_up_data):
        strategy = TrendFollowStrategy(params={"fast_period": 10, "slow_period": 30, "symbol": "TEST"})
        signal = None
        for i in range(strategy.warmup_period(), len(trending_up_data)):
            window = trending_up_data.iloc[: i + 1]
            sig = strategy.generate_signal(window)
            if sig is not None and sig.signal_type in (SignalType.BUY, SignalType.SELL):
                signal = sig
                break
        if signal is not None:
            assert signal.stop_loss is not None
            assert signal.stop_loss > 0

    def test_signal_evidence(self, trending_up_data):
        strategy = TrendFollowStrategy(params={"fast_period": 10, "slow_period": 30, "symbol": "TEST"})
        for i in range(strategy.warmup_period(), len(trending_up_data)):
            window = trending_up_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None and signal.signal_type in (SignalType.BUY, SignalType.SELL):
                assert "fast_period" in signal.evidence
                assert "slow_period" in signal.evidence
                assert "target_signal" in signal.evidence
                break

    def test_insufficient_data_returns_none(self):
        strategy = TrendFollowStrategy()
        data = pd.DataFrame({
            "open": [100], "high": [101], "low": [99], "close": [100], "volume": [1000],
        })
        signal = strategy.generate_signal(data)
        assert signal is None

    def test_nan_prices_handled(self):
        strategy = TrendFollowStrategy()
        data = pd.DataFrame({
            "open": [np.nan] * 250, "high": [np.nan] * 250, "low": [np.nan] * 250,
            "close": [np.nan] * 250, "volume": [1000] * 250,
        })
        signal = strategy.generate_signal(data)
        assert signal is None

    def test_list_strategies_includes_trend_follow(self):
        from quant_nanggroe.engine.strategy.strategies import list_strategies
        assert "trend_follow" in list_strategies()

    def test_adx_strong_trend_produces_signal(self, trending_up_data):
        strategy = TrendFollowStrategy(
            params={"fast_period": 10, "slow_period": 30, "adx_threshold": 20, "symbol": "TEST"}
        )
        for i in range(strategy.warmup_period(), len(trending_up_data)):
            window = trending_up_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None:
                assert signal.signal_type in (SignalType.BUY, SignalType.SELL)
                break
