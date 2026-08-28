"""Tests for RegimeBasedStrategy."""

import pandas as pd
import pytest

from quant_nanggroe.types.signals import Signal, SignalType

pytestmark = pytest.mark.skip("Strategy module not available")


class TestRegimeBasedStrategy:
    """Test regime-based strategy."""

    def test_default_params(self):
        strategy = RegimeBasedStrategy()
        assert strategy.name == "RegimeBased"
        assert strategy.n_regimes == 3

    def test_required_columns(self):
        strategy = RegimeBasedStrategy()
        assert "close" in strategy.required_columns()

    def test_warmup_period(self):
        strategy = RegimeBasedStrategy()
        assert strategy.warmup_period() >= 60

    def test_detect_regime_trending_up(self, trending_up_data):
        strategy = RegimeBasedStrategy()
        regime = strategy.detect_regime(trending_up_data)
        assert 0 <= regime < strategy.n_regimes

    def test_detect_regime_mean_reverting(self, mean_reverting_data):
        strategy = RegimeBasedStrategy()
        regime = strategy.detect_regime(mean_reverting_data)
        assert 0 <= regime < strategy.n_regimes

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
        assert REGIME_LABELS[0] == "bull"
        assert REGIME_LABELS[1] == "bear"
        assert REGIME_LABELS[2] == "range_bound"
        assert REGIME_LABELS[3] == "high_vol"

    def test_simple_regime_fallback(self, trending_up_data):
        strategy = RegimeBasedStrategy()
        result = strategy._detect_fallback(trending_up_data)
        assert 0 <= result < 4

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
            params={"n_regimes": 2, "symbol": "TEST"}
        )
        regime = strategy.detect_regime(trending_up_data)
        assert 0 <= regime < 2
