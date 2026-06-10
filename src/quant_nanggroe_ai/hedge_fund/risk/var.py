#!/usr/bin/env python3
"""
AI HEDGE FUND v2.3.0 - VAR Module
===================================

Value at Risk (VaR) and Conditional Value at Risk (CVaR) module.
Agent Constitution v2.3.0 Compliant

Features:
- Parametric VaR (Variance-Covariance method)
- Historical VaR (empirical distribution-based)
- Monte Carlo VaR (scenario simulation)
- CVaR / Expected Shortfall calculation
- Confidence intervals (90%, 95%, 99%, 99.9%)
- Portfolio-level calculations

Key Formulas:
- Parametric VaR: VaR_α = μ - z_α * σ (where z_α is the critical value)
- Historical VaR: Percentile-based from empirical distribution
- CVaR / Expected Shortfall: E[loss | loss > VaR_α]
- Monte Carlo: Simulate N scenarios, compute VaR from distribution

Author: Mulky Malikul Dhaher
Version: 2.3.0
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ============ DATA CLASSES ============


@dataclass
class VaRResult:
    """VaR calculation result."""

    method: str  # parametric, historical, monte_carlo, cvar
    confidence_level: str  # 90%, 95%, 99%, etc.
    var: float  # VaR value (positive = potential loss)
    expected_shortfall: float  # CVaR / Expected Shortfall
    confidence_interval: Tuple[float, float]  # (lower, upper)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfidenceLevel:
    """Confidence level for VaR."""

    percentile: float
    name: str
    color: str  # for display


@dataclass
class VaRConfig:
    """VaR configuration."""

    confidence_level: float = 0.95  # 95% by default
    window_days: int = 252  # 1 year of historical data
    min_observations: int = 30  # Minimum for VaR validity (lowered from 100)
    monte_carlo_simulations: int = 10_000  # Monte Carlo scenarios
    use_parametric: bool = True  # Use parametric if insufficient data
    fallback_method: str = "historical"  # parametric, historical, monte_carlo


# ============ CONFIDENCE LEVELS ============

CONFIDENCE_LEVELS = [
    ConfidenceLevel(percentile=0.90, name="90%", color="green"),
    ConfidenceLevel(percentile=0.95, name="95%", color="yellow"),
    ConfidenceLevel(percentile=0.99, name="99%", color="orange"),
    ConfidenceLevel(percentile=0.999, name="99.9%", color="red"),
]

# Standard normal critical values (one-tailed) for VaR
# These are z-scores such that P(Z > z) = 1 - confidence_level
CRITICAL_VALUES: Dict[float, float] = {
    0.90: 1.2816,
    0.95: 1.6449,
    0.99: 2.3263,
    0.999: 3.0902,
}


def _get_critical_value(confidence_level: float) -> float:
    """
    Get the standard normal critical value for a given confidence level.

    For VaR, we use the one-tailed critical value: P(Z > z) = 1 - α
    where α is the confidence level.

    Args:
        confidence_level: Confidence level (0.90, 0.95, 0.99, 0.999)

    Returns:
        Critical z-value.
    """
    return CRITICAL_VALUES.get(confidence_level, 1.6449)


# ============ PARAMETRIC VAR ============


class ParametricVaR:
    """
    Parametric VaR calculation (Variance-Covariance method).

    Assumes returns are normally distributed:
        VaR_α = μ - z_α * σ  (for portfolio value = 1)
        VaR_α = (μ - z_α * σ) * portfolio_value  (scaled)
    """

    MIN_OBSERVATIONS = 20

    def calculate(
        self,
        returns: np.ndarray,
        portfolio_value: float = 1.0,
        confidence_level: float = 0.95,
    ) -> VaRResult:
        """
        Calculate parametric VaR using Variance-Covariance method.

        Args:
            returns: Array of periodic returns (e.g., daily returns).
            portfolio_value: Current portfolio value.
            confidence_level: Confidence level (0.90-0.999).

        Returns:
            VaRResult with VaR and CVaR values.
        """
        if len(returns) < self.MIN_OBSERVATIONS:
            logger.warning(
                "Insufficient data for parametric VaR (need %d, got %d)",
                self.MIN_OBSERVATIONS,
                len(returns),
            )
            return VaRResult(
                method="parametric",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
            )

        returns = np.asarray(returns, dtype=np.float64)
        mean = np.mean(returns)
        std_dev = np.std(returns, ddof=1)  # Sample std dev

        if std_dev == 0:
            return VaRResult(
                method="parametric",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
            )

        z = _get_critical_value(confidence_level)

        # VaR: the maximum loss at the given confidence level
        # Express as positive number representing potential loss
        var = -(mean - z * std_dev) * portfolio_value

        # CVaR (Expected Shortfall) for normal distribution:
        # ES = -μ + σ * φ(z_α) / (1 - α)
        # where φ is the standard normal PDF
        alpha = 1.0 - confidence_level
        phi_z = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z)
        cvar = -mean * portfolio_value + std_dev * portfolio_value * phi_z / alpha

        # Confidence interval for the mean
        n = len(returns)
        se = std_dev / math.sqrt(n)
        ci_lower = (mean - 1.96 * se) * portfolio_value
        ci_upper = (mean + 1.96 * se) * portfolio_value

        return VaRResult(
            method="parametric",
            confidence_level=f"{confidence_level:.0%}",
            var=float(var),
            expected_shortfall=float(cvar),
            confidence_interval=(float(ci_lower), float(ci_upper)),
        )

    def calculate_portfolio_var(
        self,
        positions: List[Dict[str, Any]],
        weights: np.ndarray,
        returns_matrix: np.ndarray,
        confidence_level: float = 0.95,
        portfolio_value: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Calculate portfolio VaR accounting for correlations.

        Uses the variance-covariance method with the full covariance matrix:
            VaR_p = z_α * sqrt(w^T Σ w) * V

        Args:
            positions: List of position dicts with 'symbol' keys.
            weights: Portfolio weight vector (1D array summing to 1.0).
            returns_matrix: T x N matrix of returns (T periods, N assets).
            confidence_level: Confidence level.
            portfolio_value: Total portfolio value.

        Returns:
            Dict with total_var and per-position VaR breakdown.
        """
        if returns_matrix.size == 0 or len(positions) == 0:
            return {"total_var": None, "position_vars": {}}

        try:
            # Compute covariance matrix
            cov_matrix = np.cov(returns_matrix, rowvar=False)
            if cov_matrix.ndim == 0:
                # Single asset case
                cov_matrix = np.array([[float(cov_matrix)]])

            # Portfolio standard deviation
            port_var = float(weights @ cov_matrix @ weights)
            port_std = math.sqrt(port_var)

            z = _get_critical_value(confidence_level)
            total_var = z * port_std * portfolio_value

            # Per-position VaR (marginal contribution)
            position_vars: Dict[str, VaRResult] = {}
            for i, pos in enumerate(positions):
                symbol = pos.get("symbol", f"Asset_{i}")
                asset_std = math.sqrt(float(cov_matrix[i, i]))
                asset_var = z * asset_std * abs(float(weights[i])) * portfolio_value
                position_vars[symbol] = VaRResult(
                    method="portfolio_marginal",
                    confidence_level=f"{confidence_level:.0%}",
                    var=asset_var,
                    expected_shortfall=0.0,
                    confidence_interval=(0.0, 0.0),
                )

            logger.info("Portfolio VaR (%s): %.4f", f"{confidence_level:.0%}", total_var)

            return {"total_var": total_var, "position_vars": position_vars}

        except Exception as e:
            logger.error("Portfolio VaR calculation error: %s", e)
            return {"total_var": None, "position_vars": {}}


# ============ HISTORICAL VAR ============


class HistoricalVaR:
    """
    Historical VaR based on empirical distribution.

    No distributional assumptions required. Simply sorts returns
    and picks the loss at the appropriate percentile.
    """

    MIN_OBSERVATIONS = 30

    def calculate(
        self,
        returns: np.ndarray,
        portfolio_value: float = 1.0,
        confidence_level: float = 0.95,
    ) -> VaRResult:
        """
        Calculate Historical VaR using empirical distribution of returns.

        Args:
            returns: Array of periodic returns.
            portfolio_value: Current portfolio value.
            confidence_level: Confidence level (0.90-0.999).

        Returns:
            VaRResult with VaR and CVaR values.
        """
        if len(returns) < self.MIN_OBSERVATIONS:
            logger.warning(
                "Insufficient data for Historical VaR (need %d, got %d)",
                self.MIN_OBSERVATIONS,
                len(returns),
            )
            return VaRResult(
                method="historical",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
            )

        returns = np.asarray(returns, dtype=np.float64)
        sorted_returns = np.sort(returns)

        # VaR: the loss at the (1 - confidence) percentile
        # e.g., at 95% confidence, look at the 5th percentile
        alpha = 1.0 - confidence_level
        index = max(0, int(np.floor(alpha * len(sorted_returns))))
        var = -sorted_returns[index] * portfolio_value

        # CVaR / Expected Shortfall: average of losses beyond VaR
        tail_returns = sorted_returns[:index + 1]  # Worst (alpha*100)% of returns
        if len(tail_returns) > 0:
            cvar = -np.mean(tail_returns) * portfolio_value
        else:
            cvar = var

        # Bootstrap confidence interval for VaR
        n = len(returns)
        se = np.std(returns, ddof=1) / math.sqrt(n)
        ci_lower = -(np.mean(returns) + 1.96 * se) * portfolio_value
        ci_upper = -(np.mean(returns) - 1.96 * se) * portfolio_value

        return VaRResult(
            method="historical",
            confidence_level=f"{confidence_level:.0%}",
            var=float(var),
            expected_shortfall=float(cvar),
            confidence_interval=(float(ci_lower), float(ci_upper)),
        )


# ============ MONTE CARLO VAR ============


class MonteCarloVaR:
    """
    Monte Carlo VaR for scenario-based risk assessment.

    Simulates future returns by sampling from the estimated
    return distribution (assumes normality by default).
    """

    def calculate(
        self,
        returns: np.ndarray,
        portfolio_value: float = 1.0,
        confidence_level: float = 0.95,
        num_simulations: int = 10_000,
        time_horizon: int = 1,
    ) -> VaRResult:
        """
        Calculate Monte Carlo VaR through simulation.

        Args:
            returns: Array of historical returns.
            portfolio_value: Current portfolio value.
            confidence_level: Confidence level.
            num_simulations: Number of Monte Carlo scenarios.
            time_horizon: Number of periods to simulate.

        Returns:
            VaRResult with VaR and CVaR values.
        """
        returns = np.asarray(returns, dtype=np.float64)

        if len(returns) < 2:
            return VaRResult(
                method="monte_carlo",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
            )

        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        if std_return == 0:
            return VaRResult(
                method="monte_carlo",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
            )

        # Simulate returns
        np.random.seed(None)  # Use random seed for production
        simulated_returns = np.random.normal(
            loc=mean_return * time_horizon,
            scale=std_return * math.sqrt(time_horizon),
            size=num_simulations,
        )

        # Compute portfolio P&L for each scenario
        simulated_pnl = simulated_returns * portfolio_value

        # Sort P&L from worst to best
        sorted_pnl = np.sort(simulated_pnl)

        # VaR: the loss at the (1 - confidence) percentile
        alpha = 1.0 - confidence_level
        var_index = max(0, int(np.floor(alpha * num_simulations)))
        var = -sorted_pnl[var_index]

        # CVaR: average of losses beyond VaR
        tail_pnl = sorted_pnl[:var_index + 1]
        cvar = -np.mean(tail_pnl) if len(tail_pnl) > 0 else var

        # Confidence interval
        ci_lower = -sorted_pnl[min(var_index + int(0.025 * num_simulations), num_simulations - 1)]
        ci_upper = -sorted_pnl[max(var_index - int(0.025 * num_simulations), 0)]

        logger.info(
            "Monte Carlo VaR (%s): %.4f (CVaR: %.4f, %d simulations)",
            f"{confidence_level:.0%}", var, cvar, num_simulations,
        )

        return VaRResult(
            method="monte_carlo",
            confidence_level=f"{confidence_level:.0%}",
            var=float(var),
            expected_shortfall=float(cvar),
            confidence_interval=(float(ci_lower), float(ci_upper)),
        )


# ============ CVAR CALCULATOR ============


class CVaRCalculator:
    """
    Conditional Value at Risk (Expected Shortfall) calculator.

    CVaR is the expected loss given that the loss exceeds VaR:
        CVaR_α = E[Loss | Loss > VaR_α]

    For the normal distribution:
        CVaR_α = -μ + σ * φ(Φ^{-1}(1-α)) / α
    where φ is the standard normal PDF and Φ^{-1} is its inverse.
    """

    MIN_OBSERVATIONS = 30

    def calculate(
        self,
        returns: np.ndarray,
        portfolio_value: float = 1.0,
        confidence_level: float = 0.95,
    ) -> VaRResult:
        """
        Calculate CVaR (Conditional VaR / Expected Shortfall).

        Uses both the analytical formula (for normal distribution)
        and the empirical approach (for the actual data).

        Args:
            returns: Array of periodic returns.
            portfolio_value: Current portfolio value.
            confidence_level: Confidence level.

        Returns:
            VaRResult with CVaR as the primary value.
        """
        if len(returns) < self.MIN_OBSERVATIONS:
            return VaRResult(
                method="cvar",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
            )

        returns = np.asarray(returns, dtype=np.float64)
        mean = np.mean(returns)
        std_dev = np.std(returns, ddof=1)

        if std_dev == 0:
            return VaRResult(
                method="cvar",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
            )

        # Analytical CVaR for normal distribution
        z = _get_critical_value(confidence_level)
        alpha = 1.0 - confidence_level
        phi_z = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z)
        cvar_analytical = -mean + std_dev * phi_z / alpha

        # Empirical CVaR from the tail
        sorted_returns = np.sort(returns)
        var_index = max(0, int(np.floor(alpha * len(sorted_returns))))
        tail_returns = sorted_returns[:var_index + 1]
        cvar_empirical = -np.mean(tail_returns) if len(tail_returns) > 0 else 0.0

        # Use empirical if we have enough data, otherwise analytical
        if len(returns) >= 100:
            cvar = cvar_empirical * portfolio_value
            var_val = -sorted_returns[var_index] * portfolio_value
        else:
            cvar = cvar_analytical * portfolio_value
            var_val = -(mean - z * std_dev) * portfolio_value

        # Confidence interval
        n = len(returns)
        se = std_dev / math.sqrt(n)
        ci_lower = -(mean + 1.96 * se) * portfolio_value
        ci_upper = -(mean - 1.96 * se) * portfolio_value

        return VaRResult(
            method="cvar",
            confidence_level=f"{confidence_level:.0%}",
            var=float(var_val),
            expected_shortfall=float(cvar),
            confidence_interval=(float(ci_lower), float(ci_upper)),
        )


# ============ UNIFIED VAR MODULE ============


class VaRMonteCarlo:
    """
    Unified VaR module that delegates to the appropriate calculation method.

    Methods available:
    - parametric: Fast, requires normal distribution assumption
    - historical: No distribution assumption, needs more data
    - monte_carlo: Flexible simulation-based approach
    - auto: Automatically selects based on data availability
    """

    def __init__(self) -> None:
        self.parametric = ParametricVaR()
        self.historical = HistoricalVaR()
        self.monte_carlo = MonteCarloVaR()
        self.cvar = CVaRCalculator()

    def calculate(
        self,
        returns: np.ndarray,
        portfolio_value: float = 1.0,
        confidence_level: float = 0.95,
        method: str = "auto",
    ) -> VaRResult:
        """
        Unified VaR calculation that delegates to the appropriate method.

        Args:
            returns: Array of historical returns.
            portfolio_value: Current portfolio value.
            confidence_level: Confidence level (0.90, 0.95, 0.99, 0.999).
            method: Calculation method:
                - auto: Choose best method based on data availability
                - parametric: Variance-Covariance method (fast, normal assumption)
                - historical: Empirical distribution (no assumption, needs 100+ obs)
                - monte_carlo: Simulation-based (flexible, computationally intensive)
                - cvar: Direct CVaR / Expected Shortfall calculation
        """
        if method == "auto":
            if len(returns) >= 100:
                method = "historical"
            elif len(returns) >= 20:
                method = "parametric"
            else:
                method = "parametric"
            logger.info("Auto-selected VaR method: %s", method)

        if method == "parametric":
            return self.parametric.calculate(returns, portfolio_value, confidence_level)
        elif method == "historical":
            return self.historical.calculate(returns, portfolio_value, confidence_level)
        elif method == "monte_carlo":
            return self.monte_carlo.calculate(
                returns, portfolio_value, confidence_level, num_simulations=10_000,
            )
        elif method == "cvar":
            return self.cvar.calculate(returns, portfolio_value, confidence_level)
        else:
            return VaRResult(
                method="unknown",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
            )

    def calculate_portfolio_var(
        self,
        positions: List[Dict],
        weights: np.ndarray,
        returns_matrix: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Calculate portfolio VaR accounting for correlations.

        Args:
            positions: List of position dicts with symbol and details.
            weights: numpy array of position weights (should sum to 1.0).
            returns_matrix: numpy array of returns for each asset (T x N).

        Returns:
            Dictionary with total_var and position-level VaRs.
        """
        return self.parametric.calculate_portfolio_var(positions, weights, returns_matrix)


# ============ FACTORY ============


def get_var_module() -> VaRMonteCarlo:
    """Factory function to get VaR module instance."""
    logger.info("Initializing VaR Module")
    return VaRMonteCarlo()


def calculate_portfolio_var(
    positions: List[Dict],
    weights: np.ndarray,
    returns_matrix: np.ndarray,
) -> Dict[str, Any]:
    """
    Calculate portfolio VaR for a list of positions.

    Convenience function that creates a VaR module and delegates.

    Args:
        positions: List of position dicts with symbol and details.
        weights: numpy array of position weights.
        returns_matrix: numpy array of returns for each asset (T x N).

    Returns:
        Dictionary with total_var and position-level VaRs.
    """
    var_module = get_var_module()
    return var_module.calculate_portfolio_var(positions, weights, returns_matrix)
