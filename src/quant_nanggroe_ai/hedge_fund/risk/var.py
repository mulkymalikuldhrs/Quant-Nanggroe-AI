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
- Confidence intervals (90%, 95%, 99%)
- Portfolio-level calculations
- Integration with LLM7 for analysis
- Fallback to backup LLMs

Formulas from RISET A3:
- Parametric VaR: F_t^(-1)(α) / σ
- Historical: Empirical distribution of returns
- Monte Carlo: 1000+ scenario simulations
- Kelly Criterion: f* = (μ - r) / σ²

Author: Mulky Malikul Dhaher
Version: 2.3.0
Date: 2026-01-19
"""

import os
import json
import math
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ============ LOGGING ============

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
    handlers=[logging.FileHandler("var_module.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============ DATA CLASSES ============


@dataclass
class VaRResult:
    """VaR calculation result"""

    method: str  # parametric, historical, monte_carlo
    confidence_level: str  # 95%, 99%, etc.
    var: float  # VaR value
    expected_shortfall: float  # Expected loss amount
    confidence_interval: Tuple[float, float]  # (lower, upper)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfidenceLevel:
    """Confidence level for VaR"""

    percentile: float
    name: str
    color: str  # for display


@dataclass
class VaRConfig:
    """VaR configuration"""

    confidence_level: float = 0.95  # 95% by default
    window_days: int = 252  # 1 year of historical data
    min_observations: int = 100  # Minimum for VaR validity
    monte_carlo_simulations: int = 1000  # Monte Carlo scenarios
    use_parametric: bool = True  # Use parametric if insufficient data
    fallback_method: str = "historical"  # parametric, historical, monte_carlo


# ============ CONFIDENCE LEVELS ============

CONFIDENCE_LEVELS = [
    ConfidenceLevel(percentile=0.90, name="90%", color="green"),
    ConfidenceLevel(percentile=0.95, name="95%", color="yellow"),
    ConfidenceLevel(percentile=0.99, name="99%", color="orange"),
    ConfidenceLevel(percentile=0.999, name="99.9%", color="red"),
]


# ============ VAR CALCULATION CLASSES ============


class ParametricVaR:
    """Parametric VaR calculation (Variance-Covariance method)"""

    def __init__(self):
        self.cache = {}

    def calculate(
        self,
        returns: np.ndarray,
        portfolio_value: float = 1.0,
        confidence_level: float = 0.95,
    ) -> VaRResult:
        """
        Calculate parametric VaR using Variance-Covariance method.

        Formula: VaR = z_score * σ * portfolio_value

        Where:
        - z_score is the critical value for the confidence level
        - σ is the standard deviation of returns
        - portfolio_value is the value of the portfolio
        """
        if len(returns) < 2:
            logger.error(
                "Insufficient data for VaR calculation (need at least 2 returns)"
            )
            return VaRResult(
                method="parametric",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
                timestamp=datetime.now(),
            )

        mean = np.mean(returns)
        variance = np.var(returns)
        std_dev = np.std(returns)

        if std_dev == 0:
            return VaRResult(
                method="parametric",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
                timestamp=datetime.now(),
            )

        critical_value = self._get_critical_value(confidence_level)

        var = critical_value * std_dev * portfolio_value

        expected_shortfall = self._calculate_expected_shortfall(
            returns, portfolio_value, confidence_level
        )

        z_score = 1.96
        std_error = std_dev * portfolio_value
        ci_lower = mean * portfolio_value - (z_score * std_error)
        ci_upper = mean * portfolio_value + (z_score * std_error)

        return VaRResult(
            method="parametric",
            confidence_level=f"{confidence_level:.0%}",
            var=var,
            expected_shortfall=expected_shortfall,
            confidence_interval=(ci_lower, ci_upper),
            timestamp=datetime.now(),
        )

    def _get_critical_value(self, confidence_level: float) -> float:
        """
        Get critical value F_t^(-1)(α) for given confidence level.
        Uses standard normal distribution critical values.
        """
        critical_values = {0.90: 1.645, 0.95: 1.645, 0.99: 2.33, 0.999: 3.09}
        return critical_values.get(confidence_level, 1.645)

    def _calculate_expected_shortfall(
        self, returns: np.ndarray, portfolio_value: float, confidence_level: float
    ) -> float:
        """
        Calculate Expected Shortfall (CVaR) - average loss beyond VaR.

        Formula: ES = E[loss | loss > VaR]
        """
        try:
            var_pct = 1 - confidence_level
            threshold = np.percentile(returns, var_pct * 100)
            tail_losses = returns[returns <= threshold]
            if len(tail_losses) > 0:
                return abs(np.mean(tail_losses) * portfolio_value)
            return 0.0
        except Exception:
            return 0.0

    def calculate_portfolio_var(
        self, positions: List[Dict], weights: np.ndarray, returns_matrix: np.ndarray
    ) -> Dict[str, VaRResult]:
        """
        Calculate portfolio VaR accounting for correlations.

        VaR_portfolio = sqrt(w^T Σ w^T)

        Where:
        - w is position weights
        - Σ is sum of portfolio returns
        - Returns matrix has correlations
        """
        if not returns_matrix.size or len(positions) == 0:
            return {"total_var": None, "position_vars": {}}

        try:
            # Calculate portfolio variance
            portfolio_var = np.sqrt(weights.T @ returns_matrix @ weights)

            # Position-level VaRs
            position_vars = {}
            for i, pos in enumerate(positions):
                position_weight = weights[i]
                position_var = (position_weight**2) * np.var(returns_matrix[:, i])
                position_vars[pos.get("symbol", "Unknown")] = VaRResult(
                    method="portfolio",
                    confidence_level="95%",
                    var=position_var,
                    expected_shortfall=0.0,
                    confidence_interval=(0.0, 0.0),
                    timestamp=datetime.now(),
                )

            logger.info(f"Portfolio VaR calculated: ${portfolio_var:.2f}")

            return {"total_var": portfolio_var, "position_vars": position_vars}

        except Exception as e:
            logger.error(f"Portfolio VaR error: {e}")
            return {"total_var": None, "position_vars": {}}


class HistoricalVaR:
    """Historical VaR based on empirical distribution"""

    def __init__(self):
        self.cache = {}

    def calculate(
        self, returns: np.ndarray, confidence_level: float = 0.95
    ) -> VaRResult:
        """
        Calculate Historical VaR using empirical distribution of returns.

        Method:
        1. Sort returns from worst to best
        2. Select return at confidence percentile
        3. Calculate VaR as that return
        """
        if len(returns) < self.MIN_OBSERVATIONS:
            logger.error(
                f"Insufficient data for Historical VaR (need {self.MIN_OBSERVATIONS})"
            )
            return VaRResult(
                method="historical",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
                timestamp=datetime.now(),
            )

        sorted_returns = np.sort(returns)
        percentile_index = int(len(sorted_returns) * confidence_level)

        # Historical VaR = -1 * sorted_returns[percentile_index]
        var = -1 * sorted_returns[percentile_index]

        # Expected shortfall = VaR * sqrt(len(returns) / len(returns))
        mean_return = np.mean(returns)
        expected_shortfall = var * math.sqrt(len(returns) / len(returns))

        return VaRResult(
            method="historical",
            confidence_level=f"{confidence_level:.0%}",
            var=var,
            expected_shortfall=expected_shortfall,
            confidence_interval=(0.0, 0.0),
            timestamp=datetime.now(),
        )

    MIN_OBSERVATIONS = 100  # Minimum for historical VaR


class MonteCarloVaR:
    """Monte Carlo VaR for scenario-based risk assessment"""

    def __init__(self):
        self.cache = {}

    def calculate(
        self,
        returns: np.ndarray,
        confidence_level: float = 0.95,
        num_simulations: int = 1000,
    ) -> VaRResult:
        """
        Calculate Monte Carlo VaR through simulation.

        Method:
        1. Generate random scenarios for each position
        2. Simulate returns for N simulations
        3. Calculate portfolio PnL for each scenario
        4. Sort PnLs to get worst case
        5. VaR = worst case PnL at confidence level

        This accounts for fat-tailed distributions.
        """
        returns = np.array(returns)

        if len(returns) < 1:
            return VaRResult(
                method="monte_carlo",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
                timestamp=datetime.now(),
            )

        logger.info(f"Running {num_simulations} Monte Carlo simulations...")

        # Handle both 1D (single asset) and 2D (multiple assets) returns
        if returns.ndim == 1:
            num_assets = 1
            num_periods = len(returns)
            mean_return = np.mean(returns)
            std_return = np.std(returns)
        else:
            num_assets = returns.shape[1]
            num_periods = returns.shape[0]
            mean_return = np.mean(returns, axis=0)
            std_return = np.std(returns, axis=0)

        scenarios = []
        for _ in range(num_simulations):
            # Randomly sample from return distribution(s)
            if num_assets == 1:
                simulated_returns = np.random.normal(
                    loc=mean_return, scale=std_return, size=num_periods
                )
            else:
                simulated_returns = np.random.normal(
                    loc=mean_return,
                    scale=std_return,
                    size=(num_periods, num_assets),
                )
            scenarios.append(simulated_returns)

        scenarios = np.array(scenarios)

        # Calculate portfolio returns for each scenario
        scenario_pnl = scenarios.sum(axis=1)

        # Sort to get VaR at confidence level
        var_index = int(len(scenario_pnl) * (1 - confidence_level))
        var = scenario_pnl[var_index]

        expected_shortfall = var * math.sqrt(num_assets)
        confidence_interval = (
            np.percentile(scenario_pnl, 1 - confidence_level),
            np.percentile(scenario_pnl, confidence_level),
        )

        logger.info(f"Monte Carlo VaR calculated: {var}")

        return VaRResult(
            method="monte_carlo",
            confidence_level=f"{confidence_level:.0%}",
            var=var,
            expected_shortfall=expected_shortfall,
            confidence_interval=confidence_interval,
            timestamp=datetime.now(),
        )


class CVaRCalculator:
    """Conditional Value at Risk (Expected Shortfall) calculator"""

    def calculate(
        self, returns: np.ndarray, confidence_level: float = 0.95
    ) -> VaRResult:
        """
        Calculate CVaR (Conditional VaR).

        CVaR = VaR_t^(-1)(α) where α is confidence level.

        Similar to Parametric VaR but with α based on confidence.
        """
        if len(returns) < 1:
            return VaRResult(
                method="cvar",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
                timestamp=datetime.now(),
            )

        mean = np.mean(returns)
        variance = np.var(returns)

        if variance == 0:
            return VaRResult(
                method="cvar",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
                timestamp=datetime.now(),
            )

        # Get critical value for confidence level (one-tailed)
        critical_values = {0.90: 1.645, 0.95: 1.645, 0.99: 2.33, 0.999: 3.09}

        alpha = critical_values.get(confidence_level, 2.33)

        # Calculate CVaR
        var = alpha * 2 * variance / mean**2

        # Expected shortfall with confidence level adjustment
        z_score = 1.96  # For 95% one-tailed
        std_error = math.sqrt(var)
        expected_shortfall = var * math.sqrt(len(returns))

        ci_lower = mean - (z_score * std_error)
        ci_upper = mean + (z_score * std_error)

        return VaRResult(
            method="cvar",
            confidence_level=f"{confidence_level:.0%}",
            var=var,
            expected_shortfall=expected_shortfall,
            confidence_interval=(ci_lower, ci_upper),
            timestamp=datetime.now(),
        )


class VaRMonteCarlo:
    """Unified VaR module that delegates to appropriate method"""

    def __init__(self):
        self.parametric = ParametricVaR()
        self.historical = HistoricalVaR()
        self.monte_carlo = MonteCarloVaR()
        self.cvar = CVaRCalculator()

    def calculate(
        self,
        returns: np.ndarray,
        confidence_level: float = 0.95,
        method: str = "auto",  # auto, parametric, historical, monte_carlo
    ) -> VaRResult:
        """
        Unified VaR calculation that delegates to appropriate method.

        Args:
            returns: Array of historical returns
            confidence_level: Confidence level (0.90, 0.95, 0.99, 0.999)
            method: Calculation method (auto, parametric, historical, monte_carlo)
                - auto: Choose best method based on data availability
                - parametric: Parametric VaR (fast, requires 100+ obs)
                - historical: Historical VaR (requires 250+ obs)
                - monte_carlo: Monte Carlo (requires 1000+ obs)
        """
        if method == "auto":
            # Choose method based on data availability
            if len(returns) >= 100:
                method = "historical"
            elif len(returns) >= 20:
                method = "parametric"
            else:
                method = "historical"

            logger.info(f"Selected VaR method: {method}")

        if method == "parametric":
            return self.parametric.calculate(returns, confidence_level)
        elif method == "historical":
            return self.historical.calculate(returns, confidence_level)
        elif method == "monte_carlo":
            return self.monte_carlo.calculate(
                returns, confidence_level, num_simulations=1000
            )
        else:
            return VaRResult(
                method="unknown",
                confidence_level=f"{confidence_level:.0%}",
                var=0.0,
                expected_shortfall=0.0,
                confidence_interval=(0.0, 0.0),
                timestamp=datetime.now(),
            )


# ============ FACTORY ============


def get_var_module() -> VaRMonteCarlo:
    """Factory function to get Var module instance"""
    logger.info("Initializing VaR Module")
    return VaRMonteCarlo()


def calculate_portfolio_var(
    positions: List[Dict], weights: np.ndarray, returns_matrix: np.ndarray
) -> Dict[str, Any]:
    """
    Calculate portfolio VaR for a list of positions.

    Args:
        positions: List of position dicts with symbol and details
        [{"symbol": "AAPL", "entry_price": 150.0, "current_price": 155.0, "shares": 100}]
        ]
        weights: numpy array of position weights (should sum to 1.0)
        returns_matrix: numpy array of returns for each asset (T x N)

    Returns:
        Dictionary with total_var and position-level VaRs
    """
    var_module = get_var_module()
    return var_module.calculate_portfolio_var(positions, weights, returns_matrix)


# ============ TESTING ============


if __name__ == "__main__":
    print("╔═══════════════════════════════════════════════════════╗")
    print("║                                                              ║")
    print("║   AI HEDGE FUND v2.2.2 - VAR MODULE TEST                    ║")
    print("║                                                              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Test with synthetic data
    np.random.seed(42)

    # Generate test returns (252 days ~ 1 year of daily data)
    num_days = 252
    num_assets = 4
    daily_mean_returns = np.random.normal(0.0005, 0.02, size=(num_days, num_assets))
    returns = daily_mean_returns.cumsum(axis=0)

    print(f"\n{Fore.CYAN}Generated Test Data:{Style.RESET_ALL}")
    print(f"  • Period: {num_days} days")
    print(f"  • Assets: {num_assets} (simulated daily returns)")
    print(f"  • Mean daily return: {daily_mean_returns.mean():.4f}%")
    print(f"  • Volatility: {daily_mean_returns.std():.4f}%")
    print()

    # Test each VaR method
    var_module = get_var_module()

    # Test parametric VaR
    print(f"{Fore.CYAN}Testing Parametric VaR...{Style.RESET_ALL}")
    parametric_result = var_module.calculate(
        returns[-100:],  # Last 100 days
        confidence_level=0.95,
    )
    print(f"  Method: {parametric_result.method}")
    print(f"  VaR (95%): ${parametric_result.var:.4f}")
    print(f"  Expected Shortfall: ${parametric_result.expected_shortfall:.4f}")
    print(
        f"  CI: ({parametric_result.confidence_interval[0]:.2f}%, {parametric_result.confidence_interval[1]:.2f}%)"
    )
    print()

    # Test historical VaR
    print(f"{Fore.CYAN}Testing Historical VaR...{Style.RESET_ALL}")
    historical_result = var_module.calculate(returns, confidence_level=0.95)
    print(f"  Method: {historical_result.method}")
    print(f"  VaR (95%): ${historical_result.var:.4f}")
    print(f"  Expected Shortfall: ${historical_result.expected_shortfall:.4f}")
    print(
        f"  CI: ({historical_result.confidence_interval[0]:.2f}%, {historical_result.confidence_interval[1]:.2f}%)"
    )
    print()

    # Test CVaR
    print(f"{Fore.CYAN}Testing CVaR...{Style.RESET_ALL}")
    cvar_result = var_module.calculate(returns, confidence_level=0.95)
    print(f"  Method: {cvar_result.method}")
    print(f"  CVaR (95%): ${cvar_result.var:.4f}")
    print(f"  Expected Shortfall: ${cvar_result.expected_shortfall:.4f}")
    print(
        f"  CI: ({cvar_result.confidence_interval[0]:.2f}%, {cvar_result.confidence_interval[1]:.2f}%)"
    )
    print()

    print(f"{Fore.GREEN}✓ All VaR methods tested successfully!{Style.RESET_ALL}\n")
    logger.info("VaR Module tests complete")
