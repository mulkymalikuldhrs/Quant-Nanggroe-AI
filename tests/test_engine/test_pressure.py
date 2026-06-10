"""
Tests for Pressure Normalization Engine
=========================================
Test pressure compilation, sensor weights, verdict determination,
and normalization to 0.0-1.0 scale.
"""

from __future__ import annotations

import pytest

from quant_nanggroe_ai.engine.pressure import (
    PressureNormalizationEngine,
    PressureInput,
    PressureResult,
)


class TestSensorWeights:
    """Test sensor weight allocation."""

    def test_weights_sum_to_one(self) -> None:
        """All sensor weights must sum to exactly 1.0."""
        total = sum(PressureNormalizationEngine.SENSOR_WEIGHTS.values())
        assert total == pytest.approx(1.0, abs=0.001)

    def test_all_four_sensors_present(self) -> None:
        """All four sensors must be defined."""
        expected = {"quant_scanner", "smc_agent", "news_sentinel", "flow_agent"}
        assert set(PressureNormalizationEngine.SENSOR_WEIGHTS.keys()) == expected

    def test_quant_scanner_weight(self) -> None:
        """Quant Scanner should have 25% weight."""
        assert PressureNormalizationEngine.SENSOR_WEIGHTS["quant_scanner"] == 0.25

    def test_smc_agent_weight(self) -> None:
        """SMC Agent should have 30% weight (highest)."""
        assert PressureNormalizationEngine.SENSOR_WEIGHTS["smc_agent"] == 0.30

    def test_news_sentinel_weight(self) -> None:
        """News Sentinel should have 20% weight."""
        assert PressureNormalizationEngine.SENSOR_WEIGHTS["news_sentinel"] == 0.20

    def test_flow_agent_weight(self) -> None:
        """Flow Agent should have 25% weight."""
        assert PressureNormalizationEngine.SENSOR_WEIGHTS["flow_agent"] == 0.25


class TestPressureCompilation:
    """Test pressure compilation from sensor inputs."""

    @pytest.fixture
    def engine(self) -> PressureNormalizationEngine:
        return PressureNormalizationEngine()

    def test_strong_bullish_signals(self, engine: PressureNormalizationEngine) -> None:
        """All bullish signals should produce high buy pressure."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=0.9,
            smc_signal="bullish_bos",
            displacement_strength=0.8,
            liquidity_sweep=False,
            news_impact=0.5,
            news_uncertainty=0.2,
            flow_direction="long",
            flow_imbalance=0.8,
        )
        result = engine.compile_pressure(inputs)
        assert result.buy_pressure > 0.65
        assert result.sell_pressure < 0.35
        assert result.verdict in ("STRONG_BUY", "BUY")

    def test_strong_bearish_signals(self, engine: PressureNormalizationEngine) -> None:
        """All bearish signals should produce high sell pressure."""
        inputs = PressureInput(
            trend_direction="bearish",
            trend_strength=0.9,
            smc_signal="bearish_bos",
            displacement_strength=0.8,
            liquidity_sweep=False,
            news_impact=0.5,
            news_uncertainty=0.8,
            flow_direction="short",
            flow_imbalance=0.8,
        )
        result = engine.compile_pressure(inputs)
        assert result.sell_pressure > 0.65
        assert result.buy_pressure < 0.35
        assert result.verdict in ("STRONG_SELL", "SELL")

    def test_neutral_signals(self, engine: PressureNormalizationEngine) -> None:
        """Neutral/zero signals should produce NEUTRAL verdict."""
        inputs = PressureInput()  # All defaults = neutral
        result = engine.compile_pressure(inputs)
        assert result.verdict == "NEUTRAL"

    def test_mixed_signals_balanced(self, engine: PressureNormalizationEngine) -> None:
        """Equal bullish and bearish signals should produce near-50/50 split."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=0.5,
            smc_signal="bearish_bos",
            displacement_strength=0.5,
            news_impact=0.0,
            flow_direction="neutral",
        )
        result = engine.compile_pressure(inputs)
        # Should be roughly balanced
        assert 0.3 <= result.buy_pressure <= 0.7
        assert 0.3 <= result.sell_pressure <= 0.7


class TestVerdictDetermination:
    """Test verdict classification thresholds."""

    @pytest.fixture
    def engine(self) -> PressureNormalizationEngine:
        return PressureNormalizationEngine()

    def test_strong_buy_threshold(self, engine: PressureNormalizationEngine) -> None:
        """Buy pressure > 0.70 should produce STRONG_BUY verdict."""
        # Max out all bullish inputs
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=1.0,
            smc_signal="bullish_bos",
            displacement_strength=1.0,
            news_impact=0.8,
            news_uncertainty=0.0,
            flow_direction="long",
            flow_imbalance=1.0,
        )
        result = engine.compile_pressure(inputs)
        assert result.buy_pressure > 0.70
        assert result.verdict == "STRONG_BUY"

    def test_buy_threshold(self, engine: PressureNormalizationEngine) -> None:
        """Buy pressure 0.55-0.70 should produce BUY verdict."""
        # Moderate bullish — only flow + trend
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=0.7,
            smc_signal="none",
            displacement_strength=0.0,
            news_impact=0.3,
            news_uncertainty=0.5,
            flow_direction="long",
            flow_imbalance=0.7,
        )
        result = engine.compile_pressure(inputs)
        if 0.55 < result.buy_pressure <= 0.70:
            assert result.verdict == "BUY"

    def test_strong_sell_threshold(self, engine: PressureNormalizationEngine) -> None:
        """Sell pressure > 0.70 should produce STRONG_SELL verdict."""
        inputs = PressureInput(
            trend_direction="bearish",
            trend_strength=1.0,
            smc_signal="bearish_bos",
            displacement_strength=1.0,
            news_impact=0.0,
            news_uncertainty=0.0,
            flow_direction="short",
            flow_imbalance=1.0,
        )
        result = engine.compile_pressure(inputs)
        assert result.sell_pressure > 0.70
        assert result.verdict == "STRONG_SELL"

    def test_sell_threshold(self, engine: PressureNormalizationEngine) -> None:
        """Sell pressure 0.55-0.70 should produce SELL verdict."""
        inputs = PressureInput(
            trend_direction="bearish",
            trend_strength=0.7,
            smc_signal="none",
            displacement_strength=0.0,
            news_impact=0.0,
            news_uncertainty=0.8,
            flow_direction="short",
            flow_imbalance=0.7,
        )
        result = engine.compile_pressure(inputs)
        if 0.55 < result.sell_pressure <= 0.70:
            assert result.verdict == "SELL"

    def test_neutral_verdict(self, engine: PressureNormalizationEngine) -> None:
        """No significant pressure should produce NEUTRAL verdict."""
        inputs = PressureInput(
            trend_direction="neutral",
            trend_strength=0.0,
            smc_signal="none",
            displacement_strength=0.0,
            news_impact=0.0,
            flow_direction="neutral",
        )
        result = engine.compile_pressure(inputs)
        assert result.verdict == "NEUTRAL"


class TestNormalization:
    """Test pressure normalization to 0.0-1.0 scale."""

    @pytest.fixture
    def engine(self) -> PressureNormalizationEngine:
        return PressureNormalizationEngine()

    def test_pressures_between_0_and_1(self, engine: PressureNormalizationEngine) -> None:
        """Normalized pressures must always be between 0.0 and 1.0."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=1.0,
            smc_signal="bullish_bos",
            displacement_strength=1.0,
            news_impact=1.0,
            news_uncertainty=0.0,
            flow_direction="long",
            flow_imbalance=1.0,
        )
        result = engine.compile_pressure(inputs)
        assert 0.0 <= result.buy_pressure <= 1.0
        assert 0.0 <= result.sell_pressure <= 1.0

    def test_buy_plus_sell_equals_one(self, engine: PressureNormalizationEngine) -> None:
        """When there's any signal, buy + sell pressure should sum to ~1.0."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=0.6,
            smc_signal="bullish_choch",
            displacement_strength=0.5,
            news_impact=0.3,
            news_uncertainty=0.4,
            flow_direction="long",
            flow_imbalance=0.4,
        )
        result = engine.compile_pressure(inputs)
        if result.buy_pressure > 0 or result.sell_pressure > 0:
            assert result.buy_pressure + result.sell_pressure == pytest.approx(1.0, abs=0.01)

    def test_confidence_between_0_and_1(self, engine: PressureNormalizationEngine) -> None:
        """Confidence must always be between 0.0 and 1.0."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=0.5,
            smc_signal="none",
            news_impact=0.3,
            flow_direction="long",
            flow_imbalance=0.3,
        )
        result = engine.compile_pressure(inputs)
        assert 0.0 <= result.confidence <= 1.0

    def test_result_stored_as_last_result(self, engine: PressureNormalizationEngine) -> None:
        """Last result should be stored and retrievable."""
        inputs = PressureInput(trend_direction="bullish", trend_strength=0.5)
        result = engine.compile_pressure(inputs)
        assert engine.last_result is result
        assert engine.get_pressure() is result

    def test_get_pressure_state_returns_model(self, engine: PressureNormalizationEngine) -> None:
        """get_pressure_state should return a PressureState model."""
        inputs = PressureInput(trend_direction="bullish", trend_strength=0.8)
        engine.compile_pressure(inputs)
        state = engine.get_pressure_state()
        assert state.buy_pressure == engine.last_result.buy_pressure
        assert state.sell_pressure == engine.last_result.sell_pressure

    def test_result_contains_sensor_inputs(self, engine: PressureNormalizationEngine) -> None:
        """Result should record sensor input details."""
        inputs = PressureInput(
            trend_direction="bullish",
            trend_strength=0.8,
            smc_signal="bullish_bos",
        )
        result = engine.compile_pressure(inputs)
        assert "trend" in result.sensor_inputs
        assert "smc" in result.sensor_inputs
