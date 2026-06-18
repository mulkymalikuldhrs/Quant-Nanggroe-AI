"""Tests for RegimeBasedStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.strategies.regime_based import RegimeBasedStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestRegimeBasedStrategy:
    """Test regime-based strategy."""

    def test_default_params(self):
        strategy = RegimeBasedStrategy()
        assert strategy.name == "RegimeBased"
        assert strategy.n_regimes == 3
        assert strategy.confidence_threshold == 0.6

    def test_required_columns(self):
        strategy = RegimeBasedStrategy()
        assert "close" in strategy.required_columns()

    def test_warmup_period(self):
        strategy = RegimeBasedStrategy()
        assert strategy.warmup_period() >= 60

    def test_detect_regime_trending_up(self, trending_up_data):
        strategy = RegimeBasedStrategy()
        regime, probs = strategy.detect_regime(trending_up_data)
        assert 0 <= regime < strategy.n_regimes
        assert len(probs) == strategy.n_regimes
        assert abs(sum(probs) - 1.0) < 0.1  # Approximately sum to 1

    def test_detect_regime_mean_reverting(self, mean_reverting_data):
        strategy = RegimeBasedStrategy()
        regime, probs = strategy.detect_regime(mean_reverting_data)
        assert 0 <= regime < strategy.n_regimes
        assert len(probs) == strategy.n_regimes

    def test_generate_signal_trending_up(self, trending_up_data):
        strategy = RegimeBasedStrategy(
            params={"confidence_threshold": 0.3, "symbol": "TEST"}
        )
        signals = []
        for i in range(strategy.warmup_period(), len(trending_up_data)):
            window = trending_up_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None:
                signals.append(signal)

        for sig in signals:
            assert isinstance(sig, Signal)
            assert sig.signal_type in [
                SignalType.BUY, SignalType.SELL,
            ]

    def test_generate_signal_mean_reverting(self, mean_reverting_data):
        strategy = RegimeBasedStrategy(
            params={"confidence_threshold": 0.3, "symbol": "TEST"}
        )
        signals = []
        for i in range(strategy.warmup_period(), len(mean_reverting_data)):
            window = mean_reverting_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None:
                signals.append(signal)

        for sig in signals:
            assert isinstance(sig, Signal)

    def test_regime_labels(self):
        strategy = RegimeBasedStrategy()
        assert strategy.TRENDING_UP == 0
        assert strategy.TRENDING_DOWN == 1
        assert strategy.MEAN_REVERTING == 2

    def test_simple_regime_fallback(self, trending_up_data):
        strategy = RegimeBasedStrategy()
        # Force simple regime (no hmmlearn)
        result = strategy._fit_simple_regime(trending_up_data)
        assert result is True

    def test_signal_evidence_has_regime(self, trending_up_data):
        strategy = RegimeBasedStrategy(
            params={"confidence_threshold": 0.3, "symbol": "TEST"}
        )
        for i in range(strategy.warmup_period(), len(trending_up_data)):
            window = trending_up_data.iloc[: i + 1]
            signal = strategy.generate_signal(window)
            if signal is not None:
                assert "regime" in signal.evidence
                assert "regime_probs" in signal.evidence
                break

    def test_insufficient_data(self):
        strategy = RegimeBasedStrategy()
        data = pd.DataFrame({
            "open": [100], "high": [101], "low": [99],
            "close": [100], "volume": [1000],
        })
        signal = strategy.generate_signal(data)
        assert signal is None

    def test_two_regimes(self, trending_up_data):
        strategy = RegimeBasedStrategy(
            params={"n_regimes": 2, "confidence_threshold": 0.3, "symbol": "TEST"}
        )
        regime, probs = strategy.detect_regime(trending_up_data)
        assert len(probs) == 2
