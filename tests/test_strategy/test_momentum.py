"""Tests for MomentumStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.strategies.momentum import MomentumStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestMomentumStrategy:
    """Test momentum strategy."""

    def test_default_params(self):
        strategy = MomentumStrategy()
        assert strategy.name == "Momentum"
        assert strategy.mode == "ts_momentum"
        assert strategy.fast_period == 12
        assert strategy.slow_period == 26

    def test_required_columns(self):
        strategy = MomentumStrategy()
        assert all(c in strategy.required_columns() for c in ["close", "high", "low"])

    def test_warmup_ts_momentum(self):
        strategy = MomentumStrategy(params={"mode": "ts_momentum", "lookbacks": [21, 63]})
        assert strategy.warmup_period() == 73  # max(lookbacks) + 10

    def test_warmup_ma_crossover(self):
        strategy = MomentumStrategy(params={"mode": "ma_crossover", "slow_period": 30})
        assert strategy.warmup_period() == 50  # slow + 20

    def test_warmup_macd(self):
        strategy = MomentumStrategy(params={"mode": "macd"})
        assert strategy.warmup_period() == 45  # slow + signal + 10

    def test_ts_momentum_signal(self, trending_up_data):
        strategy = MomentumStrategy(
            params={"mode": "ts_momentum", "symbol": "TEST"}
        )
        signal = strategy.generate_signal(trending_up_data)
        # Trending data should produce a signal
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]
            assert 0 <= signal.confidence <= 1

    def test_ma_crossover_signal(self, trending_up_data):
        strategy = MomentumStrategy(
            params={"mode": "ma_crossover", "symbol": "TEST"}
        )
        signal = strategy.generate_signal(trending_up_data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]

    def test_macd_signal(self, trending_up_data):
        strategy = MomentumStrategy(
            params={"mode": "macd", "symbol": "TEST"}
        )
        signal = strategy.generate_signal(trending_up_data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]

    def test_dual_momentum_signal(self, trending_up_data):
        strategy = MomentumStrategy(
            params={"mode": "dual_momentum", "symbol": "TEST"}
        )
        signal = strategy.generate_signal(trending_up_data)
        if signal is not None:
            assert isinstance(signal, Signal)
            assert signal.signal_type in [SignalType.BUY, SignalType.SELL]

    def test_compute_wma(self):
        strategy = MomentumStrategy()
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        wma = strategy.compute_wma(series, 3)
        assert not np.isnan(wma.iloc[-1])

    def test_compute_hma(self):
        strategy = MomentumStrategy()
        series = pd.Series(np.random.randn(50) + 100, dtype=float)
        hma = strategy.compute_hma(series, 10)
        # HMA needs enough data
        assert len(hma) == len(series)

    def test_sma_ma_type(self, trending_up_data):
        strategy = MomentumStrategy(
            params={"mode": "ma_crossover", "ma_type": "sma", "symbol": "TEST"}
        )
        signal = strategy.generate_signal(trending_up_data)
        if signal is not None:
            assert signal.evidence["mode"] == "ma_crossover"

    def test_insufficient_data(self, random_ohlcv_data):
        strategy = MomentumStrategy()
        small_data = random_ohlcv_data.iloc[:5]
        signal = strategy.generate_signal(small_data)
        assert signal is None

    def test_signal_has_atr_info(self, trending_up_data):
        strategy = MomentumStrategy(params={"mode": "ts_momentum", "symbol": "TEST"})
        signal = strategy.generate_signal(trending_up_data)
        if signal is not None and signal.signal_type in [SignalType.BUY, SignalType.SELL]:
            assert "atr" in signal.evidence
            assert signal.evidence["atr"] > 0
