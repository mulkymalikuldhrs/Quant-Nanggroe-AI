"""Kelly Criterion — 5 Variants for Position Sizing.

Implements the Kelly Criterion for optimal position sizing with five variants:
1. Basic Kelly: f* = (bp - q) / b
2. Fractional Kelly: f* / k (where k is fraction, typically 0.5)
3. Continuous Kelly: f* = (μ - r) / σ² (for continuous-time approximation)
4. Multi-Asset Kelly: f = Σ^(-1) * μ (with covariance matrix)
5. Adaptive Kelly: Adjusts fraction based on recent performance history

Enhanced with ai-hedge-fund's Kelly module additions:
- Adaptive Kelly with performance-based fraction adjustment
- Multi-bet Kelly with correlation scaling
- Position size calculation in monetary terms
- Summary statistics across calculation history

Reference: Kelly, J. L. (1956), "A New Interpretation of Information Rate"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class KellyMethod(Enum):
    """Kelly Criterion calculation methods."""

    FULL_KELLY = "FULL_KELLY"
    HALF_KELLY = "HALF_KELLY"
    QUARTER_KELLY = "QUARTER_KELLY"
    FRACTIONAL_KELLY = "FRACTIONAL_KELLY"
    ADAPTIVE_KELLY = "ADAPTIVE_KELLY"


@dataclass
class KellyParameters:
    """Parameters for Kelly Criterion calculation.

    Attributes:
        win_rate: Probability of winning (p).
        avg_win: Average win amount.
        avg_loss: Average loss amount (positive value).
        max_loss: Maximum possible loss.
        confidence: Confidence level (0-1).
        volatility: Volatility/standard deviation.
    """

    win_rate: float
    avg_win: float
    avg_loss: float
    max_loss: Optional[float] = None
    confidence: float = 0.5
    volatility: Optional[float] = None


@dataclass
class KellyResult:
    """Result from Kelly Criterion calculation.

    Attributes:
        optimal_fraction: Optimal fraction to bet.
        expected_growth: Expected geometric growth rate.
        expected_value: Expected value of bet.
        risk_of_ruin: Probability of ruin.
        adjusted_fraction: Fraction adjusted for risk constraints.
        recommendation: Text recommendation.
        confidence: Confidence in recommendation.
    """

    optimal_fraction: float
    expected_growth: float
    expected_value: float
    risk_of_ruin: float
    adjusted_fraction: float
    recommendation: str
    confidence: float


class KellyCriterion:
    """Kelly Criterion for Optimal Position Sizing.

    The Kelly Criterion determines the optimal bet size to maximize
    long-term growth while minimizing risk of ruin.

    Supports 5 variants:
    - Basic Kelly: Standard discrete formula
    - Fractional Kelly: Reduced fraction for conservative approach
    - Continuous Kelly: Continuous-time approximation using mean/variance
    - Multi-Asset Kelly: Portfolio-level with covariance matrix
    - Adaptive Kelly: Adjusts based on recent performance history

    Config parameters:
    - max_position: Maximum position size (default: 0.20)
    - min_position: Minimum position size (default: 0.01)
    - ruin_threshold: Maximum acceptable ruin probability (default: 0.05)
    - volatility_penalty: Penalty for high volatility (default: 0.5)
    - confidence_weight: Weight for confidence adjustment (default: 0.3)
    """

    def __init__(
        self,
        max_position: float = 0.20,
        min_position: float = 0.01,
        ruin_threshold: float = 0.05,
        volatility_penalty: float = 0.5,
        confidence_weight: float = 0.3,
    ) -> None:
        self.max_position = max_position
        self.min_position = min_position
        self.ruin_threshold = ruin_threshold
        self.volatility_penalty = volatility_penalty
        self.confidence_weight = confidence_weight
        self._history: List[Dict] = []

    def calculate_kelly(
        self,
        params: KellyParameters,
        method: Optional[KellyMethod] = None,
    ) -> KellyResult:
        """Calculate Kelly Criterion.

        Args:
            params: Kelly parameters.
            method: Kelly method to use.

        Returns:
            KellyResult with optimal fraction and metrics.
        """
        if method is None:
            method = KellyMethod.HALF_KELLY

        # Calculate basic Kelly fraction
        kelly_fraction = self._calculate_basic_kelly(params)

        # Adjust for method
        adjusted = self._adjust_for_method(kelly_fraction, method)

        # Adjust for confidence
        adjusted = self._adjust_for_confidence(adjusted, params.confidence)

        # Apply constraints
        constrained = self._apply_constraints(adjusted)

        # Calculate metrics
        expected_growth = self._calculate_expected_growth(constrained, params)
        expected_value = self._calculate_expected_value(params)
        risk_of_ruin = self._calculate_risk_of_ruin(constrained, params)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            constrained, expected_growth, risk_of_ruin, method
        )

        result = KellyResult(
            optimal_fraction=kelly_fraction,
            expected_growth=expected_growth,
            expected_value=expected_value,
            risk_of_ruin=risk_of_ruin,
            adjusted_fraction=constrained,
            recommendation=recommendation,
            confidence=min(params.confidence, 1.0),
        )

        # Store in history for adaptive kelly
        self._history.append({
            "timestamp": datetime.now(),
            "params": params,
            "result": result,
            "method": method,
        })

        return result

    def calculate_continuous_kelly(
        self,
        mean_return: float,
        variance: float,
        risk_free_rate: float = 0.0,
    ) -> float:
        """Calculate continuous-time Kelly fraction.

        Formula: f* = (μ - r) / σ²

        Args:
            mean_return: Expected return (μ).
            variance: Return variance (σ²).
            risk_free_rate: Risk-free rate (r).

        Returns:
            Optimal fraction.
        """
        if variance <= 0:
            return 0.0
        return (mean_return - risk_free_rate) / variance

    def calculate_multi_asset_kelly(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        risk_free_rate: float = 0.0,
    ) -> np.ndarray:
        """Calculate multi-asset Kelly weights.

        Formula: f = Σ^(-1) * (μ - r)

        Args:
            expected_returns: Vector of expected returns.
            cov_matrix: Covariance matrix.
            risk_free_rate: Risk-free rate.

        Returns:
            Vector of optimal weights.
        """
        try:
            excess_returns = expected_returns - risk_free_rate
            inv_cov = np.linalg.inv(cov_matrix)
            weights = inv_cov @ excess_returns
            # Normalize if total exceeds 1
            total = np.sum(np.abs(weights))
            if total > 1.0:
                weights /= total
            return weights
        except np.linalg.LinAlgError:
            return np.zeros(len(expected_returns))

    def calculate_multi_bet_kelly(
        self,
        params_list: List[KellyParameters],
        method: Optional[KellyMethod] = None,
    ) -> List[KellyResult]:
        """Calculate Kelly Criterion for multiple simultaneous bets.

        For multiple bets, the optimal allocation is given by:
            f = C^(-1) * m
        Where C is the covariance matrix and m is the expected return vector.

        In this simplified implementation, individual Kelly fractions are
        calculated and then scaled to respect the max position constraint.

        Args:
            params_list: List of Kelly parameters for each bet.
            method: Kelly method to use.

        Returns:
            List of Kelly results, scaled for correlation.
        """
        if not params_list:
            return []

        results = []
        for params in params_list:
            result = self.calculate_kelly(params, method)
            results.append(result)

        # Adjust for correlation (simplified scaling)
        if len(results) > 1:
            total_fraction = sum(r.adjusted_fraction for r in results)
            if total_fraction > self.max_position:
                scale_factor = self.max_position / total_fraction
                for result in results:
                    result.adjusted_fraction *= scale_factor

        return results

    def get_optimal_position_size(
        self,
        account_value: float,
        params: KellyParameters,
        method: Optional[KellyMethod] = None,
    ) -> float:
        """Get optimal position size in monetary terms.

        Args:
            account_value: Total account value.
            params: Kelly parameters.
            method: Kelly method.

        Returns:
            Position size in currency.
        """
        result = self.calculate_kelly(params, method)
        return account_value * result.adjusted_fraction

    def get_summary_statistics(self) -> Dict:
        """Get summary statistics of Kelly calculations.

        Returns:
            Dict with aggregate statistics across all calculations.
        """
        if not self._history:
            return {"total_calculations": 0}

        total = len(self._history)
        avg_fraction = np.mean([h["result"].adjusted_fraction for h in self._history])
        avg_growth = np.mean([h["result"].expected_growth for h in self._history])
        avg_risk = np.mean([h["result"].risk_of_ruin for h in self._history])

        positive_growth = sum(
            1 for h in self._history if h["result"].expected_growth > 0
        )

        return {
            "total_calculations": total,
            "average_fraction": round(avg_fraction, 4),
            "average_expected_growth": round(avg_growth, 6),
            "average_risk_of_ruin": round(avg_risk, 4),
            "positive_growth_rate": round(positive_growth / total, 4),
            "total_capital_at_risk": round(avg_fraction * 100, 2),
        }

    @staticmethod
    def _calculate_basic_kelly(params: KellyParameters) -> float:
        """Calculate basic Kelly fraction: f* = (bp - q) / b."""
        if params.avg_loss <= 0:
            return 0.0

        p = params.win_rate
        q = 1.0 - p
        b = params.avg_win / params.avg_loss

        kelly_fraction = (b * p - q) / b if b > 0 else 0.0
        return max(0.0, kelly_fraction)

    def _adjust_for_method(self, fraction: float, method: KellyMethod) -> float:
        """Adjust fraction based on Kelly method."""
        if method == KellyMethod.FULL_KELLY:
            return fraction
        elif method == KellyMethod.HALF_KELLY:
            return fraction * 0.5
        elif method == KellyMethod.QUARTER_KELLY:
            return fraction * 0.25
        elif method == KellyMethod.FRACTIONAL_KELLY:
            return fraction * 0.5
        elif method == KellyMethod.ADAPTIVE_KELLY:
            return self._calculate_adaptive_kelly(fraction)
        else:
            return fraction * 0.5

    def _calculate_adaptive_kelly(self, fraction: float) -> float:
        """Calculate adaptive Kelly based on historical performance.

        Starts with half Kelly, then adjusts based on recent win rate:
        - Recent win rate > 60%: Use 75% of full Kelly
        - Recent win rate > 50%: Use 50% of full Kelly
        - Recent win rate <= 50%: Use 25% of full Kelly
        """
        if len(self._history) < 10:
            return fraction * 0.5

        # Calculate recent win rate from history
        recent_results = self._history[-20:]
        win_count = sum(1 for h in recent_results if h["result"].expected_value > 0)
        recent_win_rate = win_count / len(recent_results)

        # Adjust fraction based on recent performance
        if recent_win_rate > 0.6:
            return fraction * 0.75  # Increase to 75% Kelly
        elif recent_win_rate > 0.5:
            return fraction * 0.5  # Maintain 50% Kelly
        else:
            return fraction * 0.25  # Decrease to 25% Kelly

    def _adjust_for_confidence(self, fraction: float, confidence: float) -> float:
        """Adjust fraction based on confidence level."""
        return fraction * (1.0 - self.confidence_weight * (1.0 - confidence))

    def _apply_constraints(self, fraction: float) -> float:
        """Apply risk constraints to fraction."""
        if fraction > self.max_position:
            fraction = self.max_position
        if 0 < fraction < self.min_position:
            fraction = self.min_position
        if fraction < 0:
            fraction = 0.0
        return fraction

    @staticmethod
    def _calculate_expected_growth(fraction: float, params: KellyParameters) -> float:
        """Calculate expected geometric growth rate: G = p*log(1+bf) + q*log(1-f)."""
        if params.avg_loss <= 0:
            return 0.0
        p = params.win_rate
        q = 1.0 - p
        b = params.avg_win / params.avg_loss

        try:
            return p * np.log(1 + b * fraction) + q * np.log(1 - fraction)
        except (ValueError, ZeroDivisionError):
            return 0.0

    @staticmethod
    def _calculate_expected_value(params: KellyParameters) -> float:
        """Calculate expected value: EV = p*avg_win - q*avg_loss."""
        return params.win_rate * params.avg_win - (1.0 - params.win_rate) * params.avg_loss

    @staticmethod
    def _calculate_risk_of_ruin(fraction: float, params: KellyParameters) -> float:
        """Calculate approximate probability of ruin.

        Risk of Ruin ≈ ((1 - f) / (1 + bf))^(p/q)
        """
        if params.avg_loss <= 0 or fraction <= 0:
            return 0.0

        p = params.win_rate
        q = 1.0 - p
        b = params.avg_win / params.avg_loss

        if 1 + b * fraction <= 0 or 1 - fraction <= 0:
            return 1.0

        try:
            base = (1 - fraction) / (1 + b * fraction)
            return min(float(base ** (p / q)), 1.0)
        except (ZeroDivisionError, ValueError):
            return 1.0

    @staticmethod
    def _generate_recommendation(
        fraction: float,
        expected_growth: float,
        risk_of_ruin: float,
        method: KellyMethod,
    ) -> str:
        """Generate text recommendation."""
        if expected_growth < 0:
            return "AVOID - Negative expected growth"
        if risk_of_ruin > 0.05:
            return f"AVOID - High risk of ruin ({risk_of_ruin:.2%})"
        if fraction <= 0:
            return "NO POSITION - No edge detected"
        if fraction >= 0.20:
            return f"MAX POSITION - Strong edge ({method.value})"
        if fraction >= 0.15:
            return f"LARGE POSITION - Good edge ({method.value})"
        if fraction >= 0.10:
            return f"MEDIUM POSITION - Moderate edge ({method.value})"
        return f"SMALL POSITION - Weak edge ({method.value})"
