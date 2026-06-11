"""Value at Risk (VaR) — Parametric, Historical, Monte Carlo.

Implements three VaR methods with CVaR (Expected Shortfall) as the
PRIMARY risk metric (not just VaR).

Methods:
1. Parametric VaR: Variance-Covariance method (assumes normal distribution)
2. Historical VaR: Empirical distribution-based
3. Monte Carlo VaR: Scenario simulation

CVaR is preferred over VaR because:
- VaR only tells you the threshold, not the magnitude of tail losses
- CVaR captures the expected loss BEYOND the VaR threshold
- CVaR is a coherent risk measure (sub-additive, convex)
- CVaR is more conservative and appropriate for risk management

Extracted from ai-hedge-fund's VaR module with corrections and enhancements.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class VaRResult:
    """VaR calculation result."""

    method: str
    confidence_level: float
    var_value: float
    cvar_value: float  # CVaR is the PRIMARY metric
    confidence_interval: Tuple[float, float]


class VaRCalculator:
    """Unified VaR Calculator with CVaR as primary metric.

    Provides three calculation methods and automatically selects
    the most appropriate based on data availability.

    IMPORTANT: CVaR (Conditional Value at Risk / Expected Shortfall)
    is used as the PRIMARY risk metric, not VaR. CVaR captures the
    expected magnitude of losses beyond the VaR threshold.
    """

    def __init__(self, default_confidence: float = 0.95) -> None:
        self.default_confidence = default_confidence

    def calculate(
        self,
        returns: np.ndarray,
        confidence_level: float = 0.95,
        method: str = "auto",
        portfolio_value: float = 1.0,
        num_simulations: int = 10000,
    ) -> VaRResult:
        """Calculate VaR and CVaR.

        Args:
            returns: Array of historical returns.
            confidence_level: Confidence level (0.90, 0.95, 0.99).
            method: 'auto', 'parametric', 'historical', 'monte_carlo'.
            portfolio_value: Portfolio value for monetary VaR.
            num_simulations: Simulations for Monte Carlo method.

        Returns:
            VaRResult with VaR and CVaR values.
        """
        returns = np.asarray(returns, dtype=np.float64)
        returns = returns[~np.isnan(returns)]

        if len(returns) < 2:
            return VaRResult(
                method="insufficient_data",
                confidence_level=confidence_level,
                var_value=0.0,
                cvar_value=0.0,
                confidence_interval=(0.0, 0.0),
            )

        if method == "auto":
            method = self._select_method(len(returns))

        if method == "parametric":
            return self._parametric_var(returns, confidence_level, portfolio_value)
        elif method == "historical":
            return self._historical_var(returns, confidence_level, portfolio_value)
        elif method == "monte_carlo":
            return self._monte_carlo_var(returns, confidence_level, portfolio_value, num_simulations)
        else:
            return self._historical_var(returns, confidence_level, portfolio_value)

    @staticmethod
    def _select_method(n_observations: int) -> str:
        """Select the most appropriate VaR method based on data availability."""
        if n_observations >= 500:
            return "historical"
        elif n_observations >= 100:
            return "parametric"
        else:
            return "parametric"

    def _parametric_var(
        self,
        returns: np.ndarray,
        confidence_level: float,
        portfolio_value: float,
    ) -> VaRResult:
        """Parametric VaR (Variance-Covariance method).

        Assumes returns are normally distributed.
        Formula: VaR = z_α * σ * V
        CVaR = σ * φ(z_α) / (1 - α) * V

        Where φ is the standard normal PDF.
        """
        from scipy import stats

        mean = np.mean(returns)
        std = np.std(returns, ddof=1)

        if std <= 0:
            return VaRResult("parametric", confidence_level, 0.0, 0.0, (0.0, 0.0))

        z_alpha = stats.norm.ppf(1 - confidence_level)
        var_value = abs(z_alpha * std * portfolio_value)

        # CVaR for normal distribution
        cvar_value = std * stats.norm.pdf(z_alpha) / (1 - confidence_level) * portfolio_value

        # Confidence interval for the mean
        z_95 = 1.96
        se = std / np.sqrt(len(returns))
        ci = (
            (mean - z_95 * se) * portfolio_value,
            (mean + z_95 * se) * portfolio_value,
        )

        return VaRResult("parametric", confidence_level, var_value, cvar_value, ci)

    def _historical_var(
        self,
        returns: np.ndarray,
        confidence_level: float,
        portfolio_value: float,
    ) -> VaRResult:
        """Historical VaR using empirical distribution.

        Simply takes the percentile of the empirical return distribution.
        """
        alpha = 1 - confidence_level

        # VaR: the (1-α) percentile of losses
        var_threshold = np.percentile(returns, alpha * 100)
        var_value = abs(var_threshold * portfolio_value)

        # CVaR: mean of losses beyond VaR
        tail_returns = returns[returns <= var_threshold]
        cvar_value = abs(np.mean(tail_returns) * portfolio_value) if len(tail_returns) > 0 else var_value

        # Bootstrap confidence interval
        ci = self._bootstrap_ci(returns, alpha, portfolio_value)

        return VaRResult("historical", confidence_level, var_value, cvar_value, ci)

    def _monte_carlo_var(
        self,
        returns: np.ndarray,
        confidence_level: float,
        portfolio_value: float,
        num_simulations: int,
    ) -> VaRResult:
        """Monte Carlo VaR through simulation.

        Generates random scenarios from the fitted distribution
        and computes VaR/CVaR from the simulated distribution.
        """
        from scipy import stats

        mean = np.mean(returns)
        std = np.std(returns, ddof=1)
        alpha = 1 - confidence_level

        # Fit t-distribution for better tail modeling
        try:
            df_t, loc_t, scale_t = stats.t.fit(returns)
            simulated = stats.t.rvs(df_t, loc=loc_t, scale=scale_t, size=num_simulations)
        except Exception:
            simulated = np.random.normal(mean, std, size=num_simulations)

        var_threshold = np.percentile(simulated, alpha * 100)
        var_value = abs(var_threshold * portfolio_value)

        tail_sim = simulated[simulated <= var_threshold]
        cvar_value = abs(np.mean(tail_sim) * portfolio_value) if len(tail_sim) > 0 else var_value

        ci = (
            np.percentile(simulated, alpha * 100 - 1.96) * portfolio_value,
            np.percentile(simulated, alpha * 100 + 1.96) * portfolio_value,
        )

        return VaRResult("monte_carlo", confidence_level, var_value, cvar_value, ci)

    @staticmethod
    def _bootstrap_ci(
        returns: np.ndarray,
        alpha: float,
        portfolio_value: float,
        n_bootstrap: int = 1000,
    ) -> Tuple[float, float]:
        """Bootstrap confidence interval for VaR."""
        var_samples = []
        n = len(returns)
        for _ in range(n_bootstrap):
            sample = np.random.choice(returns, size=n, replace=True)
            var_samples.append(np.percentile(sample, alpha * 100))

        return (
            abs(np.percentile(var_samples, 2.5)) * portfolio_value,
            abs(np.percentile(var_samples, 97.5)) * portfolio_value,
        )
