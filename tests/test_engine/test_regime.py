"""
Tests for Market Regime Detection Engine (HMM)
===============================================
Tests regime detection, statistical fallback, transition matrices,
cross-validation, and price-to-return conversion.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from quant_nanggroe_ai.engine.regime import (
    RegimeDetectionEngine,
    RegimeClassification,
    RegimeProbability,
    RegimeDetectionResult,
    HMMConfig,
    RegimeTransitionMatrix,
    HMM_AVAILABLE,
)
from quant_nanggroe_ai.types import MarketRegime
from quant_nanggroe_ai.exceptions import InsufficientDataError


# ══════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def engine() -> RegimeDetectionEngine:
    """Fresh engine with default config."""
    return RegimeDetectionEngine()


@pytest.fixture
def bull_returns() -> list[float]:
    """Returns consistent with a bull market."""
    np.random.seed(42)
    return (np.random.normal(0.001, 0.008, 100)).tolist()


@pytest.fixture
def bear_returns() -> list[float]:
    """Returns consistent with a bear market."""
    np.random.seed(42)
    return (np.random.normal(-0.001, 0.02, 100)).tolist()


@pytest.fixture
def sideways_returns() -> list[float]:
    """Returns consistent with sideways market."""
    np.random.seed(42)
    return (np.random.normal(0.0, 0.003, 100)).tolist()


@pytest.fixture
def volatile_returns() -> list[float]:
    """Returns consistent with a volatile market."""
    np.random.seed(42)
    return (np.random.normal(0.0, 0.03, 100)).tolist()


@pytest.fixture
def prices_from_returns() -> list[float]:
    """Generate price series from returns for detect_from_prices."""
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.01, 100)
    prices = [100.0]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    return prices


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODEL TESTS
# ══════════════════════════════════════════════════════════════════════


class TestRegimeClassification:
    def test_values(self) -> None:
        assert RegimeClassification.BULL == "BULL"
        assert RegimeClassification.BEAR == "BEAR"
        assert RegimeClassification.SIDEWAYS == "SIDEWAYS"
        assert RegimeClassification.VOLATILE == "VOLATILE"


class TestRegimeProbability:
    def test_defaults(self) -> None:
        rp = RegimeProbability()
        assert rp.bull == 0.25
        assert rp.bear == 0.25
        assert rp.sideways == 0.25
        assert rp.volatile == 0.25

    def test_bounds(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RegimeProbability(bull=-0.1)
        with pytest.raises(ValidationError):
            RegimeProbability(bull=1.1)


class TestRegimeDetectionResult:
    def test_defaults(self) -> None:
        result = RegimeDetectionResult()
        assert result.current_regime == RegimeClassification.SIDEWAYS
        assert result.confidence == 0.0
        assert result.method == "HMM"
        assert result.market_regime_enum == MarketRegime.UNKNOWN

    def test_custom(self) -> None:
        result = RegimeDetectionResult(
            current_regime="BULL",
            confidence=0.9,
            method="STATISTICAL_FALLBACK",
        )
        assert result.current_regime == "BULL"
        assert result.confidence == 0.9


class TestHMMConfig:
    def test_defaults(self) -> None:
        config = HMMConfig()
        assert config.n_components == 4
        assert config.min_observations == 50
        assert config.random_state == 42

    def test_bounds(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            HMMConfig(n_components=1)  # Too few
        with pytest.raises(ValidationError):
            HMMConfig(n_components=9)  # Too many

    def test_custom(self) -> None:
        config = HMMConfig(n_components=3, min_observations=30)
        assert config.n_components == 3
        assert config.min_observations == 30


class TestRegimeTransitionMatrix:
    def test_defaults(self) -> None:
        tm = RegimeTransitionMatrix()
        matrix = tm.matrix
        assert "BULL" in matrix
        assert "BEAR" in matrix
        # Each row should sum to approximately 1
        for regime, transitions in matrix.items():
            assert abs(sum(transitions.values()) - 1.0) < 0.05


# ══════════════════════════════════════════════════════════════════════
# REGIME DETECTION ENGINE TESTS
# ══════════════════════════════════════════════════════════════════════


class TestEngineFitting:
    """Test model fitting (both HMM and fallback)."""

    def test_fit_with_sufficient_data(self, engine: RegimeDetectionEngine) -> None:
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 100).tolist()
        result = engine.fit(returns)
        assert result["status"] == "FITTED"
        assert engine.is_fitted is True

    def test_fit_method_type(self, engine: RegimeDetectionEngine) -> None:
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 100).tolist()
        result = engine.fit(returns)
        if HMM_AVAILABLE:
            assert result["method"] == "HMM"
        else:
            assert result["method"] == "STATISTICAL_FALLBACK"

    def test_fit_insufficient_data(self, engine: RegimeDetectionEngine) -> None:
        with pytest.raises(InsufficientDataError):
            engine.fit([0.01] * 10)

    def test_fit_with_custom_config(self) -> None:
        config = HMMConfig(n_components=2, min_observations=30)
        engine = RegimeDetectionEngine(config=config)
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 50).tolist()
        result = engine.fit(returns)
        assert result["status"] == "FITTED"


class TestRegimeDetection:
    """Test regime detection from returns."""

    def test_detect_bull_regime(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        result = engine.detect_current_regime()
        assert result.current_regime in ("BULL", "SIDEWAYS", "VOLATILE")
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0
        assert result.regime_probability is not None

    def test_detect_bear_regime(
        self, engine: RegimeDetectionEngine, bear_returns: list[float]
    ) -> None:
        engine.fit(bear_returns)
        result = engine.detect_current_regime()
        assert result.current_regime in ("BEAR", "VOLATILE", "SIDEWAYS")

    def test_detect_volatile_regime(
        self, engine: RegimeDetectionEngine, volatile_returns: list[float]
    ) -> None:
        engine.fit(volatile_returns)
        result = engine.detect_current_regime()
        assert result.current_regime in ("VOLATILE", "BEAR", "SIDEWAYS")

    def test_detect_with_no_data(self, engine: RegimeDetectionEngine) -> None:
        result = engine.detect_current_regime()
        assert result.current_regime == RegimeClassification.SIDEWAYS
        assert result.confidence == 0.0
        assert result.method == "NO_DATA"

    def test_detect_with_explicit_returns(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        # Override with sideways returns
        sideways = [0.0] * 50 + [0.001] * 50
        result = engine.detect_current_regime(recent_returns=sideways)
        assert result.current_regime in (
            "BULL", "BEAR", "SIDEWAYS", "VOLATILE",
        )

    def test_detection_result_has_transition_matrix(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        result = engine.detect_current_regime()
        assert isinstance(result.transition_matrix, dict)

    def test_detection_result_has_regime_history(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        result = engine.detect_current_regime()
        assert isinstance(result.regime_history, list)

    def test_detection_result_has_duration(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        result = engine.detect_current_regime()
        assert result.duration_in_regime >= 1

    def test_detection_result_has_likely_transition(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        result = engine.detect_current_regime()
        # likely_transition can be None if only one regime detected
        assert result.likely_transition is None or isinstance(
            result.likely_transition, str
        )

    def test_detection_result_has_market_regime_enum(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        result = engine.detect_current_regime()
        assert isinstance(result.market_regime_enum, MarketRegime)

    def test_multiple_detections_build_history(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        engine.detect_current_regime()
        engine.detect_current_regime()
        engine.detect_current_regime()
        result = engine.detect_current_regime()
        assert result.duration_in_regime >= 1


class TestDetectFromPrices:
    """Test regime detection from price data."""

    def test_detect_from_prices(
        self,
        engine: RegimeDetectionEngine,
        prices_from_returns: list[float],
    ) -> None:
        result = engine.detect_from_prices(prices_from_returns)
        assert result.current_regime in (
            "BULL", "BEAR", "SIDEWAYS", "VOLATILE",
        )

    def test_detect_from_prices_insufficient(
        self, engine: RegimeDetectionEngine
    ) -> None:
        with pytest.raises(InsufficientDataError):
            engine.detect_from_prices([100.0])

    def test_detect_from_prices_auto_fits(
        self, engine: RegimeDetectionEngine
    ) -> None:
        """Should auto-fit if not already fitted and enough data."""
        np.random.seed(42)
        prices = [100.0]
        for _ in range(200):
            prices.append(prices[-1] * (1 + np.random.normal(0.0005, 0.01)))

        result = engine.detect_from_prices(prices)
        assert result.current_regime in (
            "BULL", "BEAR", "SIDEWAYS", "VOLATILE",
        )


class TestCrossValidation:
    """Test cross-validation with MarketStateEngine."""

    def test_cross_validate_without_result(self, engine: RegimeDetectionEngine) -> None:
        result = engine.cross_validate_with_market_state(MarketRegime.TRENDING_UP)
        assert result["status"] == "NO_HMM_RESULT"

    def test_cross_validate_agreement(
        self,
        engine: RegimeDetectionEngine,
        bull_returns: list[float],
    ) -> None:
        engine.fit(bull_returns)
        engine.detect_current_regime()

        # Cross-validate with any regime — just test it returns valid dict
        result = engine.cross_validate_with_market_state(MarketRegime.TRENDING_UP)
        assert "hmm_regime" in result
        assert "market_state_regime" in result
        assert "agrees" in result
        assert isinstance(result["agrees"], bool)


class TestHelperMethods:
    """Test internal helper methods via their public effects."""

    def test_classify_by_thresholds_bull(self) -> None:
        result = RegimeDetectionEngine._classify_by_thresholds(0.001, 0.008)
        assert result == "BULL"

    def test_classify_by_thresholds_bear(self) -> None:
        result = RegimeDetectionEngine._classify_by_thresholds(-0.001, 0.008)
        assert result == "BEAR"

    def test_classify_by_thresholds_sideways(self) -> None:
        result = RegimeDetectionEngine._classify_by_thresholds(0.0, 0.005)
        assert result == "SIDEWAYS"

    def test_classify_by_thresholds_volatile(self) -> None:
        result = RegimeDetectionEngine._classify_by_thresholds(0.0, 0.03)
        assert result == "VOLATILE"

    def test_to_market_regime_mapping(self) -> None:
        assert RegimeDetectionEngine._to_market_regime("BULL") == MarketRegime.TRENDING_UP
        assert RegimeDetectionEngine._to_market_regime("BEAR") == MarketRegime.TRENDING_DOWN
        assert RegimeDetectionEngine._to_market_regime("SIDEWAYS") == MarketRegime.RANGE
        assert RegimeDetectionEngine._to_market_regime("VOLATILE") == MarketRegime.VOLATILE
        assert RegimeDetectionEngine._to_market_regime("UNKNOWN") == MarketRegime.UNKNOWN

    def test_to_hmm_regime_label(self) -> None:
        assert RegimeDetectionEngine._to_hmm_regime_label(MarketRegime.TRENDING_UP) == "BULL"
        assert RegimeDetectionEngine._to_hmm_regime_label(MarketRegime.TRENDING_DOWN) == "BEAR"
        assert RegimeDetectionEngine._to_hmm_regime_label(MarketRegime.RANGE) == "SIDEWAYS"
        assert RegimeDetectionEngine._to_hmm_regime_label(MarketRegime.VOLATILE) == "VOLATILE"
        assert RegimeDetectionEngine._to_hmm_regime_label(MarketRegime.CALM) == "SIDEWAYS"
        assert RegimeDetectionEngine._to_hmm_regime_label(MarketRegime.RISK_OFF) == "BEAR"
        assert RegimeDetectionEngine._to_hmm_regime_label(MarketRegime.PANIC) == "VOLATILE"


class TestEngineStatus:
    """Test engine status reporting."""

    def test_status_not_fitted(self, engine: RegimeDetectionEngine) -> None:
        status = engine.status()
        assert status["is_fitted"] is False
        assert status["last_regime"] is None
        assert "hmm_available" in status
        assert "regime_mapping" in status

    def test_status_after_fit(
        self, engine: RegimeDetectionEngine, bull_returns: list[float]
    ) -> None:
        engine.fit(bull_returns)
        engine.detect_current_regime()
        status = engine.status()
        assert status["is_fitted"] is True
        assert status["last_regime"] is not None
        assert status["last_confidence"] is not None

    def test_hmm_available_property(self, engine: RegimeDetectionEngine) -> None:
        assert isinstance(engine.hmm_available, bool)

    def test_transition_matrix_property(self, engine: RegimeDetectionEngine) -> None:
        tm = engine.transition_matrix
        assert isinstance(tm, RegimeTransitionMatrix)
