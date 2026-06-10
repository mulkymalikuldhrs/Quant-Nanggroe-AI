"""
Monte Carlo Simulation Engine
==============================
From Quant-Nanggroe-AI — Probabilistic portfolio risk and trajectory analysis.

Simulates portfolio value trajectories using configurable stochastic processes:
  - Geometric Brownian Motion (GBM) for standard price paths
  - Regime-aware simulation with transition dynamics
  - Walk-forward simulation with regime detection integration
  - VaR and CVaR estimation via simulation

All simulations are deterministic given the same random seed.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from quant_nanggroe_ai.config import MAX_DAILY_LOSS, MAX_WEEKLY_LOSS
from quant_nanggroe_ai.exceptions import InsufficientDataError, InvalidParameterError
from quant_nanggroe_ai.logging import get_logger
from quant_nanggroe_ai.types import MarketRegime

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════


class SimulationConfig(BaseModel):
    """Configuration for a Monte Carlo simulation run."""

    num_paths: int = Field(
        default=10_000,
        ge=100,
        le=1_000_000,
        description="Number of simulation paths",
    )
    time_steps: int = Field(
        default=252,
        ge=10,
        le=5_000,
        description="Number of time steps (e.g., 252 = 1 year of trading days)",
    )
    initial_value: float = Field(
        default=100_000.0,
        gt=0,
        description="Initial portfolio value",
    )
    annual_drift: float = Field(
        default=0.08,
        description="Annual expected return (drift)",
    )
    annual_volatility: float = Field(
        default=0.20,
        gt=0,
        description="Annual volatility (diffusion)",
    )
    dt: float = Field(
        default=1.0 / 252,
        gt=0,
        description="Time step size in years",
    )
    random_seed: int | None = Field(
        default=42,
        description="Random seed for reproducibility",
    )


class SimulationResult(BaseModel):
    """Result of a Monte Carlo simulation run."""

    config: SimulationConfig
    final_values: list[float] = Field(
        default_factory=list,
        description="Terminal portfolio values for each path",
    )
    mean_final_value: float = 0.0
    median_final_value: float = 0.0
    std_final_value: float = 0.0
    min_final_value: float = 0.0
    max_final_value: float = 0.0
    var_95: float = Field(default=0.0, description="Value at Risk at 95% confidence")
    var_99: float = Field(default=0.0, description="Value at Risk at 99% confidence")
    cvar_95: float = Field(default=0.0, description="CVaR (Expected Shortfall) at 95%")
    cvar_99: float = Field(default=0.0, description="CVaR (Expected Shortfall) at 99%")
    prob_of_loss: float = Field(default=0.0, description="Probability of any loss")
    prob_of_max_daily_loss: float = Field(
        default=0.0,
        description="Probability of exceeding max daily loss",
    )
    path_trajectories: list[list[float]] = Field(
        default_factory=list,
        description="Sample trajectories (up to 100 stored)",
    )
    timestamp: datetime = Field(default_factory=datetime.now)


class RegimeSimulationConfig(BaseModel):
    """Configuration for regime-aware Monte Carlo simulation."""

    base_config: SimulationConfig = Field(default_factory=SimulationConfig)
    regime_params: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "BULL": {"drift": 0.15, "volatility": 0.12},
            "BEAR": {"drift": -0.10, "volatility": 0.30},
            "SIDEWAYS": {"drift": 0.02, "volatility": 0.10},
            "VOLATILE": {"drift": 0.0, "volatility": 0.40},
        },
        description="Regime-specific drift and volatility parameters",
    )
    transition_matrix: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "BULL": {"BULL": 0.90, "BEAR": 0.05, "SIDEWAYS": 0.03, "VOLATILE": 0.02},
            "BEAR": {"BULL": 0.05, "BEAR": 0.85, "SIDEWAYS": 0.05, "VOLATILE": 0.05},
            "SIDEWAYS": {"BULL": 0.10, "BEAR": 0.10, "SIDEWAYS": 0.70, "VOLATILE": 0.10},
            "VOLATILE": {"BULL": 0.15, "BEAR": 0.15, "SIDEWAYS": 0.10, "VOLATILE": 0.60},
        },
        description="Regime transition probability matrix",
    )
    initial_regime: str = Field(
        default="BULL",
        description="Starting regime for simulation",
    )


class WalkForwardSimulationResult(BaseModel):
    """Result of a walk-forward simulation with regime detection."""

    windows: list[dict[str, Any]] = Field(default_factory=list)
    aggregated_var_95: float = 0.0
    aggregated_cvar_95: float = 0.0
    regime_distribution: dict[str, float] = Field(
        default_factory=dict,
        description="Fraction of time spent in each regime",
    )
    timestamp: datetime = Field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# MONTE CARLO SIMULATION ENGINE
# ══════════════════════════════════════════════════════════════════════


class MonteCarloSimulationEngine:
    """
    Monte Carlo simulation engine for portfolio risk analysis.

    Features:
    - Geometric Brownian Motion (GBM) for price path simulation
    - Regime-aware simulation with Markov chain transitions
    - Walk-forward simulation with rolling regime detection
    - VaR/CVaR estimation from simulated distributions
    - Configurable number of paths and time steps
    - Deterministic output given the same random seed

    All calculations are production-quality with proper error handling
    and integration with the project's config, logging, and exceptions.
    """

    MAX_TRAJECTORY_SAMPLES = 100  # Maximum number of trajectories to store

    def __init__(self, config: SimulationConfig | None = None) -> None:
        """
        Initialize the simulation engine.

        Args:
            config: Optional simulation configuration. Uses defaults if not provided.
        """
        self._config = config or SimulationConfig()
        self._last_result: SimulationResult | None = None

    @property
    def config(self) -> SimulationConfig:
        """Get current simulation configuration."""
        return self._config

    @property
    def last_result(self) -> SimulationResult | None:
        """Get the result of the last simulation run."""
        return self._last_result

    # ══════════════════════════════════════════════════════════════════
    # Geometric Brownian Motion
    # ══════════════════════════════════════════════════════════════════

    def simulate_gbm(self, config: SimulationConfig | None = None) -> SimulationResult:
        """
        Simulate portfolio trajectories using Geometric Brownian Motion.

        GBM stochastic differential equation:
            dS = μ·S·dt + σ·S·dW

        Discretized (Euler-Maruyama):
            S(t+dt) = S(t) · exp((μ - 0.5·σ²)·dt + σ·√dt·Z)

        where Z ~ N(0,1)

        Args:
            config: Optional override for simulation configuration.

        Returns:
            SimulationResult with terminal values, VaR/CVaR, and sample trajectories.

        Raises:
            InvalidParameterError: If configuration parameters are invalid.
        """
        cfg = config or self._config
        self._validate_config(cfg)

        if cfg.random_seed is not None:
            np.random.seed(cfg.random_seed)

        # Pre-compute constants
        drift_dt = (cfg.annual_drift - 0.5 * cfg.annual_volatility ** 2) * cfg.dt
        vol_sqrt_dt = cfg.annual_volatility * math.sqrt(cfg.dt)

        # Generate all random numbers at once (vectorized for performance)
        z = np.random.standard_normal((cfg.num_paths, cfg.time_steps))

        # Compute log returns for all paths and time steps
        log_returns = drift_dt + vol_sqrt_dt * z

        # Cumulative sum to get log price paths
        cum_log_returns = np.cumsum(log_returns, axis=1)

        # Terminal values: S_T = S_0 * exp(sum of log returns)
        final_values = cfg.initial_value * np.exp(cum_log_returns[:, -1])

        # Store sample trajectories (up to MAX_TRAJECTORY_SAMPLES)
        num_samples = min(self.MAX_TRAJECTORY_SAMPLES, cfg.num_paths)
        sample_indices = np.linspace(0, cfg.num_paths - 1, num_samples, dtype=int)
        trajectories: list[list[float]] = []

        for idx in sample_indices:
            path = [cfg.initial_value]
            for t in range(cfg.time_steps):
                path.append(cfg.initial_value * np.exp(cum_log_returns[idx, t]))
            trajectories.append(path)

        # Compute statistics
        result = self._compute_simulation_statistics(cfg, final_values.tolist(), trajectories)

        self._last_result = result
        logger.info(
            "gbm_simulation_complete",
            num_paths=cfg.num_paths,
            time_steps=cfg.time_steps,
            mean_final=round(result.mean_final_value, 2),
            var_95=round(result.var_95, 2),
            cvar_95=round(result.cvar_95, 2),
            prob_of_loss=round(result.prob_of_loss, 4),
        )

        return result

    # ══════════════════════════════════════════════════════════════════
    # Regime-Aware Simulation
    # ══════════════════════════════════════════════════════════════════

    def simulate_regime_aware(
        self, config: RegimeSimulationConfig | None = None
    ) -> SimulationResult:
        """
        Simulate portfolio trajectories with regime-switching dynamics.

        Uses a Markov chain to model regime transitions, where each regime
        has its own drift and volatility parameters. This captures the
        empirically observed phenomenon that markets alternate between
        distinct behavioral states (bull, bear, sideways, volatile).

        Args:
            config: Regime-aware simulation configuration. Uses defaults if not provided.

        Returns:
            SimulationResult with regime-aware terminal values and risk metrics.
        """
        cfg = config or RegimeSimulationConfig()
        base = cfg.base_config

        if base.random_seed is not None:
            np.random.seed(base.random_seed)

        self._validate_config(base)
        self._validate_regime_config(cfg)

        # Build transition matrix as numpy array
        regime_names = sorted(cfg.regime_params.keys())
        n_regimes = len(regime_names)
        regime_idx = {name: i for i, name in enumerate(regime_names)}

        trans_matrix = np.zeros((n_regimes, n_regimes))
        for from_regime, transitions in cfg.transition_matrix.items():
            for to_regime, prob in transitions.items():
                if from_regime in regime_idx and to_regime in regime_idx:
                    trans_matrix[regime_idx[from_regime], regime_idx[to_regime]] = prob

        # Normalize rows (ensure probabilities sum to 1)
        row_sums = trans_matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0  # Avoid division by zero
        trans_matrix = trans_matrix / row_sums

        # Regime-specific parameters
        regime_drifts = np.array([cfg.regime_params[r]["drift"] for r in regime_names])
        regime_vols = np.array([cfg.regime_params[r]["volatility"] for r in regime_names])

        # Run simulation
        initial_regime_idx = regime_idx.get(cfg.initial_regime, 0)
        final_values = np.zeros(base.num_paths)
        trajectories: list[list[float]] = []
        num_samples = min(self.MAX_TRAJECTORY_SAMPLES, base.num_paths)
        sample_indices = set(
            np.linspace(0, base.num_paths - 1, num_samples, dtype=int).tolist()
        )

        for p in range(base.num_paths):
            current_value = base.initial_value
            current_regime = initial_regime_idx
            path: list[float] = [current_value] if p in sample_indices else []

            for t in range(base.time_steps):
                # Regime transition (Markov chain step)
                current_regime = np.random.choice(n_regimes, p=trans_matrix[current_regime])

                # GBM step with regime-specific parameters
                drift = regime_drifts[current_regime]
                vol = regime_vols[current_regime]
                drift_dt = (drift - 0.5 * vol ** 2) * base.dt
                vol_sqrt_dt = vol * math.sqrt(base.dt)
                z = np.random.standard_normal()

                current_value *= np.exp(drift_dt + vol_sqrt_dt * z)

                if p in sample_indices:
                    path.append(current_value)

            final_values[p] = current_value
            if path:
                trajectories.append(path)

        result = self._compute_simulation_statistics(base, final_values.tolist(), trajectories)
        self._last_result = result

        logger.info(
            "regime_aware_simulation_complete",
            num_paths=base.num_paths,
            time_steps=base.time_steps,
            initial_regime=cfg.initial_regime,
            mean_final=round(result.mean_final_value, 2),
            var_95=round(result.var_95, 2),
        )

        return result

    # ══════════════════════════════════════════════════════════════════
    # Walk-Forward Simulation
    # ══════════════════════════════════════════════════════════════════

    def simulate_walk_forward(
        self,
        historical_returns: list[float],
        window_size: int = 252,
        n_windows: int = 5,
        num_paths: int = 1_000,
        config: SimulationConfig | None = None,
    ) -> WalkForwardSimulationResult:
        """
        Walk-forward simulation with regime detection from historical returns.

        For each rolling window:
        1. Estimate drift and volatility from the window
        2. Detect the current regime using volatility and drift
        3. Run a mini Monte Carlo simulation for the next period
        4. Aggregate results across windows

        This approach combines the rigor of walk-forward analysis with
        the probabilistic insights of Monte Carlo simulation.

        Args:
            historical_returns: Historical portfolio returns (daily)
            window_size: Size of each rolling window in trading days
            n_windows: Number of walk-forward windows
            num_paths: Number of simulation paths per window
            config: Base simulation configuration (overrides defaults)

        Returns:
            WalkForwardSimulationResult with aggregated risk metrics.

        Raises:
            InsufficientDataError: If not enough historical returns provided.
        """
        min_required = window_size + n_windows
        if len(historical_returns) < min_required:
            raise InsufficientDataError(
                required=min_required,
                actual=len(historical_returns),
                indicator="walk_forward_simulation",
            )

        base_cfg = config or self._config
        all_var_95: list[float] = []
        all_cvar_95: list[float] = []
        regime_counts: dict[str, int] = {}
        windows: list[dict[str, Any]] = []

        for w in range(n_windows):
            start = w * (window_size // n_windows)
            end = start + window_size
            if end > len(historical_returns):
                break

            window_returns = np.array(historical_returns[start:end])

            # Estimate parameters from window
            drift = float(np.mean(window_returns)) * 252  # Annualize
            vol = float(np.std(window_returns, ddof=1)) * math.sqrt(252)  # Annualize

            # Detect regime
            regime = self._detect_regime_from_params(drift, vol)
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

            # Run mini simulation for this window
            window_cfg = SimulationConfig(
                num_paths=num_paths,
                time_steps=window_size,
                initial_value=base_cfg.initial_value,
                annual_drift=drift,
                annual_volatility=vol,
                dt=1.0 / 252,
                random_seed=base_cfg.random_seed,
            )

            sim_result = self.simulate_gbm(window_cfg)

            all_var_95.append(sim_result.var_95)
            all_cvar_95.append(sim_result.cvar_95)

            windows.append(
                {
                    "window_idx": w,
                    "start": start,
                    "end": end,
                    "estimated_drift": round(drift, 4),
                    "estimated_volatility": round(vol, 4),
                    "detected_regime": regime,
                    "var_95": round(sim_result.var_95, 2),
                    "cvar_95": round(sim_result.cvar_95, 2),
                    "prob_of_loss": round(sim_result.prob_of_loss, 4),
                }
            )

        # Aggregate results
        total_regime_count = sum(regime_counts.values()) or 1
        regime_distribution = {
            k: round(v / total_regime_count, 4) for k, v in regime_counts.items()
        }

        result = WalkForwardSimulationResult(
            windows=windows,
            aggregated_var_95=round(float(np.mean(all_var_95)), 2) if all_var_95 else 0.0,
            aggregated_cvar_95=round(float(np.mean(all_cvar_95)), 2) if all_cvar_95 else 0.0,
            regime_distribution=regime_distribution,
        )

        logger.info(
            "walk_forward_simulation_complete",
            n_windows=len(windows),
            avg_var_95=result.aggregated_var_95,
            avg_cvar_95=result.aggregated_cvar_95,
            regime_distribution=regime_distribution,
        )

        return result

    # ══════════════════════════════════════════════════════════════════
    # VaR/CVaR from Simulation
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def compute_var_cvar(
        final_values: list[float],
        initial_value: float,
        confidence_levels: list[float] | None = None,
    ) -> dict[str, float]:
        """
        Compute VaR and CVaR from simulated terminal portfolio values.

        VaR at confidence level α: the maximum loss not exceeded with
        probability α. CVaR (Expected Shortfall): the expected loss
        given that the loss exceeds VaR.

        Args:
            final_values: Terminal portfolio values from simulation
            initial_value: Initial portfolio value for loss calculation
            confidence_levels: Confidence levels for VaR/CVaR (default: [0.95, 0.99])

        Returns:
            Dict with VaR and CVaR at each confidence level
        """
        if not final_values:
            return {"var_95": 0.0, "cvar_95": 0.0, "var_99": 0.0, "cvar_99": 0.0}

        confidence_levels = confidence_levels or [0.95, 0.99]
        arr = np.array(final_values)
        losses = initial_value - arr  # Loss = initial - final (positive = loss)

        result: dict[str, float] = {}

        for cl in confidence_levels:
            pct = (1 - cl) * 100
            var_threshold = float(np.percentile(losses, cl * 100))  # cl-th percentile of losses
            var_value = max(0.0, var_threshold)

            # CVaR: average of losses exceeding VaR
            tail_losses = losses[losses >= var_threshold]
            cvar_value = float(np.mean(tail_losses)) if len(tail_losses) > 0 else var_value
            cvar_value = max(0.0, cvar_value)

            cl_key = f"{int(cl * 100)}"
            result[f"var_{cl_key}"] = round(var_value, 2)
            result[f"cvar_{cl_key}"] = round(cvar_value, 2)

        return result

    # ══════════════════════════════════════════════════════════════════
    # Helper Methods
    # ══════════════════════════════════════════════════════════════════

    def _compute_simulation_statistics(
        self,
        config: SimulationConfig,
        final_values: list[float],
        trajectories: list[list[float]],
    ) -> SimulationResult:
        """
        Compute summary statistics from simulation terminal values.

        Args:
            config: Simulation configuration used
            final_values: Terminal portfolio values from all paths
            trajectories: Sample path trajectories

        Returns:
            SimulationResult with all computed statistics
        """
        arr = np.array(final_values)

        # Basic statistics
        mean_final = float(np.mean(arr))
        median_final = float(np.median(arr))
        std_final = float(np.std(arr, ddof=1))
        min_final = float(np.min(arr))
        max_final = float(np.max(arr))

        # VaR and CVaR
        var_cvar = self.compute_var_cvar(final_values, config.initial_value)

        # Probability of loss
        prob_of_loss = float(np.mean(arr < config.initial_value))

        # Probability of exceeding max daily loss
        max_daily_loss_value = config.initial_value * MAX_DAILY_LOSS
        prob_max_daily = float(np.mean(config.initial_value - arr > max_daily_loss_value))

        return SimulationResult(
            config=config,
            final_values=final_values,
            mean_final_value=round(mean_final, 2),
            median_final_value=round(median_final, 2),
            std_final_value=round(std_final, 2),
            min_final_value=round(min_final, 2),
            max_final_value=round(max_final, 2),
            var_95=var_cvar.get("var_95", 0.0),
            var_99=var_cvar.get("var_99", 0.0),
            cvar_95=var_cvar.get("cvar_95", 0.0),
            cvar_99=var_cvar.get("cvar_99", 0.0),
            prob_of_loss=round(prob_of_loss, 4),
            prob_of_max_daily_loss=round(prob_max_daily, 4),
            path_trajectories=trajectories,
        )

    @staticmethod
    def _detect_regime_from_params(annual_drift: float, annual_vol: float) -> str:
        """
        Classify market regime from estimated drift and volatility.

        Args:
            annual_drift: Annualized return estimate
            annual_vol: Annualized volatility estimate

        Returns:
            Regime string: BULL, BEAR, SIDEWAYS, or VOLATILE
        """
        if annual_vol > 0.30:
            return "VOLATILE"
        elif annual_drift > 0.05:
            return "BULL"
        elif annual_drift < -0.05:
            return "BEAR"
        else:
            return "SIDEWAYS"

    @staticmethod
    def _validate_config(config: SimulationConfig) -> None:
        """Validate simulation configuration parameters."""
        if config.initial_value <= 0:
            raise InvalidParameterError(
                "initial_value", config.initial_value, "Must be positive"
            )
        if config.annual_volatility <= 0:
            raise InvalidParameterError(
                "annual_volatility", config.annual_volatility, "Must be positive"
            )
        if config.time_steps <= 0:
            raise InvalidParameterError(
                "time_steps", config.time_steps, "Must be positive"
            )
        if config.num_paths <= 0:
            raise InvalidParameterError(
                "num_paths", config.num_paths, "Must be positive"
            )

    @staticmethod
    def _validate_regime_config(config: RegimeSimulationConfig) -> None:
        """Validate regime-aware simulation configuration."""
        if not config.regime_params:
            raise InvalidParameterError(
                "regime_params", config.regime_params, "Must define at least one regime"
            )

        for regime_name, params in config.regime_params.items():
            if "drift" not in params:
                raise InvalidParameterError(
                    f"regime_params[{regime_name}]", params, "Must include 'drift'"
                )
            if "volatility" not in params:
                raise InvalidParameterError(
                    f"regime_params[{regime_name}]", params, "Must include 'volatility'"
                )
            if params["volatility"] <= 0:
                raise InvalidParameterError(
                    f"regime_params[{regime_name}].volatility",
                    params["volatility"],
                    "Must be positive",
                )

        if config.initial_regime not in config.regime_params:
            raise InvalidParameterError(
                "initial_regime",
                config.initial_regime,
                f"Must be one of {list(config.regime_params.keys())}",
            )

    def status(self) -> dict[str, Any]:
        """Get current simulation engine status."""
        return {
            "config": self._config.model_dump(),
            "last_simulation": self._last_result.model_dump() if self._last_result else None,
            "timestamp": datetime.now().isoformat(),
        }
