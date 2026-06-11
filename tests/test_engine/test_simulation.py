"""
Tests for Monte Carlo Simulation Engine
========================================
Tests GBM simulation, regime-aware simulation, walk-forward simulation,
VaR/CVaR computation, and configuration validation.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from quant_nanggroe_ai.engine.simulation import (
    MonteCarloSimulationEngine,
    SimulationConfig,
    SimulationResult,
    RegimeSimulationConfig,
    WalkForwardSimulationResult,
)
from quant_nanggroe_ai.exceptions import InsufficientDataError, InvalidParameterError


# ══════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════


@pytest.fixture
def engine() -> MonteCarloSimulationEngine:
    """Fresh simulation engine."""
    return MonteCarloSimulationEngine()


@pytest.fixture
def fast_config() -> SimulationConfig:
    """Fast simulation config for unit tests."""
    return SimulationConfig(
        num_paths=500,
        time_steps=50,
        initial_value=100000.0,
        annual_drift=0.08,
        annual_volatility=0.20,
        random_seed=42,
    )


@pytest.fixture
def fast_regime_config() -> RegimeSimulationConfig:
    """Fast regime-aware simulation config."""
    return RegimeSimulationConfig(
        base_config=SimulationConfig(
            num_paths=200,
            time_steps=30,
            initial_value=100000.0,
            annual_drift=0.08,
            annual_volatility=0.20,
            random_seed=42,
        ),
        regime_params={
            "BULL": {"drift": 0.15, "volatility": 0.12},
            "BEAR": {"drift": -0.10, "volatility": 0.30},
        },
        transition_matrix={
            "BULL": {"BULL": 0.90, "BEAR": 0.10},
            "BEAR": {"BULL": 0.10, "BEAR": 0.90},
        },
        initial_regime="BULL",
    )


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODEL TESTS
# ══════════════════════════════════════════════════════════════════════


class TestSimulationConfig:
    def test_defaults(self) -> None:
        config = SimulationConfig()
        assert config.num_paths == 10_000
        assert config.time_steps == 252
        assert config.initial_value == 100_000.0
        assert config.annual_drift == 0.08
        assert config.annual_volatility == 0.20
        assert config.random_seed == 42

    def test_bounds(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SimulationConfig(num_paths=10)  # Below 100
        with pytest.raises(ValidationError):
            SimulationConfig(initial_value=-100)  # Must be positive
        with pytest.raises(ValidationError):
            SimulationConfig(annual_volatility=-0.1)  # Must be positive

    def test_custom(self) -> None:
        config = SimulationConfig(
            num_paths=1000, time_steps=100, initial_value=50000.0,
        )
        assert config.num_paths == 1000


class TestRegimeSimulationConfig:
    def test_defaults(self) -> None:
        config = RegimeSimulationConfig()
        assert "BULL" in config.regime_params
        assert "BEAR" in config.regime_params
        assert config.initial_regime == "BULL"


class TestSimulationResult:
    def test_defaults(self) -> None:
        result = SimulationResult(config=SimulationConfig())
        assert result.mean_final_value == 0.0
        assert result.var_95 == 0.0


# ══════════════════════════════════════════════════════════════════════
# GBM SIMULATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestGBMSimulation:
    """Test Geometric Brownian Motion simulation."""

    def test_basic_simulation(
        self, engine: MonteCarloSimulationEngine, fast_config: SimulationConfig
    ) -> None:
        result = engine.simulate_gbm(fast_config)
        assert isinstance(result, SimulationResult)
        assert result.mean_final_value > 0
        assert result.min_final_value > 0
        assert result.max_final_value >= result.mean_final_value

    def test_deterministic_with_seed(
        self, engine: MonteCarloSimulationEngine, fast_config: SimulationConfig
    ) -> None:
        result1 = engine.simulate_gbm(fast_config)
        result2 = engine.simulate_gbm(fast_config)
        assert result1.mean_final_value == result2.mean_final_value

    def test_statistics_are_reasonable(
        self, engine: MonteCarloSimulationEngine, fast_config: SimulationConfig
    ) -> None:
        result = engine.simulate_gbm(fast_config)
        # With 8% drift, mean final value should generally be above initial
        # (though not guaranteed for all seeds, it's very likely for 500 paths)
        assert result.median_final_value > 0
        assert result.std_final_value > 0
        assert result.var_95 >= 0
        assert result.var_99 >= 0
        assert result.cvar_95 >= result.var_95  # CVaR >= VaR
        assert result.cvar_99 >= result.var_99

    def test_prob_of_loss_in_range(
        self, engine: MonteCarloSimulationEngine, fast_config: SimulationConfig
    ) -> None:
        result = engine.simulate_gbm(fast_config)
        assert 0.0 <= result.prob_of_loss <= 1.0

    def test_trajectories_stored(
        self, engine: MonteCarloSimulationEngine, fast_config: SimulationConfig
    ) -> None:
        result = engine.simulate_gbm(fast_config)
        assert len(result.path_trajectories) > 0
        # Each trajectory starts at initial value
        for traj in result.path_trajectories:
            assert abs(traj[0] - fast_config.initial_value) < 0.01

    def test_override_config(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        custom = SimulationConfig(
            num_paths=200, time_steps=20, initial_value=50000.0,
            annual_drift=0.15, annual_volatility=0.10, random_seed=99,
        )
        result = engine.simulate_gbm(custom)
        assert result.config.num_paths == 200

    def test_last_result_stored(
        self, engine: MonteCarloSimulationEngine, fast_config: SimulationConfig
    ) -> None:
        result = engine.simulate_gbm(fast_config)
        assert engine.last_result is not None
        assert engine.last_result.mean_final_value == result.mean_final_value

    def test_zero_drift(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        config = SimulationConfig(
            num_paths=500, time_steps=50, annual_drift=0.0,
            annual_volatility=0.20, random_seed=42,
        )
        result = engine.simulate_gbm(config)
        # With zero drift, mean should be near initial (on average)
        assert result.mean_final_value > 0

    def test_high_volatility(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        config = SimulationConfig(
            num_paths=500, time_steps=50, annual_volatility=0.50,
            annual_drift=0.0, random_seed=42,
        )
        result = engine.simulate_gbm(config)
        assert result.std_final_value > 0
        assert result.prob_of_loss > 0.1  # Likely to have losses with high vol


# ══════════════════════════════════════════════════════════════════════
# REGIME-AWARE SIMULATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestRegimeAwareSimulation:
    """Test regime-aware Monte Carlo simulation."""

    def test_basic_regime_aware(
        self,
        engine: MonteCarloSimulationEngine,
        fast_regime_config: RegimeSimulationConfig,
    ) -> None:
        result = engine.simulate_regime_aware(fast_regime_config)
        assert isinstance(result, SimulationResult)
        assert result.mean_final_value > 0
        assert result.var_95 >= 0

    def test_regime_aware_deterministic(
        self,
        engine: MonteCarloSimulationEngine,
        fast_regime_config: RegimeSimulationConfig,
    ) -> None:
        result1 = engine.simulate_regime_aware(fast_regime_config)
        result2 = engine.simulate_regime_aware(fast_regime_config)
        assert result1.mean_final_value == result2.mean_final_value

    def test_regime_aware_with_default_config(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        # Use default regime config but with fast base
        config = RegimeSimulationConfig(
            base_config=SimulationConfig(
                num_paths=100, time_steps=20, random_seed=42,
            ),
        )
        result = engine.simulate_regime_aware(config)
        assert result.mean_final_value > 0

    def test_regime_aware_invalid_regime_params(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        config = RegimeSimulationConfig(
            base_config=SimulationConfig(
                num_paths=100, time_steps=20, random_seed=42,
            ),
            regime_params={},
        )
        with pytest.raises(InvalidParameterError, match="regime_params"):
            engine.simulate_regime_aware(config)

    def test_regime_aware_missing_drift(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        config = RegimeSimulationConfig(
            base_config=SimulationConfig(
                num_paths=100, time_steps=20, random_seed=42,
            ),
            regime_params={"BULL": {"volatility": 0.12}},  # Missing drift
        )
        with pytest.raises(InvalidParameterError, match="drift"):
            engine.simulate_regime_aware(config)

    def test_regime_aware_missing_volatility(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        config = RegimeSimulationConfig(
            base_config=SimulationConfig(
                num_paths=100, time_steps=20, random_seed=42,
            ),
            regime_params={"BULL": {"drift": 0.15}},  # Missing volatility
        )
        with pytest.raises(InvalidParameterError, match="volatility"):
            engine.simulate_regime_aware(config)

    def test_regime_aware_negative_volatility(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        config = RegimeSimulationConfig(
            base_config=SimulationConfig(
                num_paths=100, time_steps=20, random_seed=42,
            ),
            regime_params={"BULL": {"drift": 0.15, "volatility": -0.1}},
        )
        with pytest.raises(InvalidParameterError, match="positive"):
            engine.simulate_regime_aware(config)

    def test_regime_aware_invalid_initial_regime(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        config = RegimeSimulationConfig(
            base_config=SimulationConfig(
                num_paths=100, time_steps=20, random_seed=42,
            ),
            regime_params={"BULL": {"drift": 0.15, "volatility": 0.12}},
            initial_regime="NONEXISTENT",
        )
        with pytest.raises(InvalidParameterError, match="initial_regime"):
            engine.simulate_regime_aware(config)


# ══════════════════════════════════════════════════════════════════════
# WALK-FORWARD SIMULATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestWalkForwardSimulation:
    """Test walk-forward simulation with regime detection."""

    def test_basic_walk_forward(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.015, 300).tolist()
        result = engine.simulate_walk_forward(
            historical_returns=returns,
            window_size=50,
            n_windows=3,
            num_paths=100,
        )
        assert isinstance(result, WalkForwardSimulationResult)
        assert len(result.windows) == 3
        assert result.aggregated_var_95 >= 0
        assert result.aggregated_cvar_95 >= 0

    def test_walk_forward_regime_distribution(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.015, 300).tolist()
        result = engine.simulate_walk_forward(
            historical_returns=returns,
            window_size=50,
            n_windows=3,
            num_paths=100,
        )
        assert len(result.regime_distribution) > 0
        # Distribution values should sum to ~1.0
        total = sum(result.regime_distribution.values())
        assert abs(total - 1.0) < 0.01

    def test_walk_forward_insufficient_data(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        with pytest.raises(InsufficientDataError):
            engine.simulate_walk_forward(
                historical_returns=[0.01] * 10,
                window_size=50,
                n_windows=3,
            )

    def test_walk_forward_window_fields(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.015, 300).tolist()
        result = engine.simulate_walk_forward(
            historical_returns=returns,
            window_size=50,
            n_windows=2,
            num_paths=100,
        )
        for window in result.windows:
            assert "window_idx" in window
            assert "estimated_drift" in window
            assert "estimated_volatility" in window
            assert "detected_regime" in window
            assert "var_95" in window


# ══════════════════════════════════════════════════════════════════════
# VAR/CVAR COMPUTATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestVarCvarComputation:
    """Test standalone VaR/CVaR computation."""

    def test_basic_computation(self) -> None:
        # Final values below initial → losses
        final_values = [80000.0, 85000.0, 90000.0, 95000.0, 100000.0,
                        105000.0, 110000.0, 115000.0, 120000.0, 125000.0]
        result = MonteCarloSimulationEngine.compute_var_cvar(
            final_values=final_values,
            initial_value=100000.0,
        )
        assert result["var_95"] >= 0
        assert result["cvar_95"] >= 0
        assert result["var_99"] >= 0
        assert result["cvar_99"] >= 0

    def test_empty_final_values(self) -> None:
        result = MonteCarloSimulationEngine.compute_var_cvar(
            final_values=[], initial_value=100000.0,
        )
        assert result["var_95"] == 0.0
        assert result["cvar_95"] == 0.0

    def test_all_gains_no_var(self) -> None:
        # All final values above initial → no losses
        final_values = [110000.0] * 100
        result = MonteCarloSimulationEngine.compute_var_cvar(
            final_values=final_values,
            initial_value=100000.0,
        )
        # VaR should be 0 since no losses
        assert result["var_95"] == 0.0

    def test_custom_confidence_levels(self) -> None:
        final_values = list(range(50000, 150000, 1000))
        result = MonteCarloSimulationEngine.compute_var_cvar(
            final_values=final_values,
            initial_value=100000.0,
            confidence_levels=[0.90, 0.95],
        )
        assert "var_90" in result
        assert "cvar_90" in result
        assert "var_95" in result
        assert "cvar_95" in result


# ══════════════════════════════════════════════════════════════════════
# HELPER / VALIDATION TESTS
# ══════════════════════════════════════════════════════════════════════


class TestHelperMethods:
    """Test helper and validation methods."""

    def test_detect_regime_from_params_bull(self) -> None:
        result = MonteCarloSimulationEngine._detect_regime_from_params(0.10, 0.15)
        assert result == "BULL"

    def test_detect_regime_from_params_bear(self) -> None:
        result = MonteCarloSimulationEngine._detect_regime_from_params(-0.10, 0.15)
        assert result == "BEAR"

    def test_detect_regime_from_params_volatile(self) -> None:
        result = MonteCarloSimulationEngine._detect_regime_from_params(0.0, 0.40)
        assert result == "VOLATILE"

    def test_detect_regime_from_params_sideways(self) -> None:
        result = MonteCarloSimulationEngine._detect_regime_from_params(0.02, 0.10)
        assert result == "SIDEWAYS"

    def test_validate_config_positive_initial_value(self) -> None:
        config = SimulationConfig(initial_value=100000.0)
        # Should not raise
        MonteCarloSimulationEngine._validate_config(config)

    def test_validate_config_negative_initial_value(self) -> None:
        # Bypass Pydantic validation to test internal validation
        config = SimulationConfig(initial_value=100000.0)
        config.initial_value = -100.0  # Force invalid after creation
        with pytest.raises(InvalidParameterError, match="initial_value"):
            MonteCarloSimulationEngine._validate_config(config)


class TestEngineProperties:
    """Test engine properties and status."""

    def test_config_property(self) -> None:
        config = SimulationConfig(num_paths=500)
        engine = MonteCarloSimulationEngine(config=config)
        assert engine.config.num_paths == 500

    def test_last_result_none_initially(
        self, engine: MonteCarloSimulationEngine
    ) -> None:
        assert engine.last_result is None

    def test_status(self, engine: MonteCarloSimulationEngine) -> None:
        status = engine.status()
        assert "config" in status
        assert "timestamp" in status
