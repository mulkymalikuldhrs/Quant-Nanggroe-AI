"""
Kelly Criterion for Position Sizing v2.3.0
Implements optimal position sizing based on expected returns and risk
Agent Constitution v2.3.0 Compliant

Key Components:
- Kelly Criterion: Optimal bet size
- Partial Kelly: Fractional Kelly for risk management
- Multiple Simultaneous Bets: Multi-bet Kelly
- Confidence Adjustment: Adjust based on confidence level
- Risk Constraints: Maximum position limits

Formula:
f* = (bp - q) / b

Where:
- f* = fraction of bankroll to wager
- b = odds received on the wager (b to 1)
- p = probability of winning
- q = probability of losing (1 - p)
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KellyMethod(Enum):
    """Kelly Criterion calculation methods"""

    FULL_KELLY = "FULL_KELLY"
    HALF_KELLY = "HALF_KELLY"
    QUARTER_KELLY = "QUARTER_KELLY"
    FRACTIONAL_KELLY = "FRACTIONAL_KELLY"
    ADAPTIVE_KELLY = "ADAPTIVE_KELLY"


@dataclass
class KellyParameters:
    """Parameters for Kelly Criterion calculation"""

    win_rate: float  # Probability of winning (p)
    avg_win: float  # Average win amount
    avg_loss: float  # Average loss amount (positive value)
    max_loss: Optional[float] = None  # Maximum possible loss
    confidence: float = 0.5  # Confidence level (0-1)
    volatility: Optional[float] = None  # Volatility/standard deviation


@dataclass
class KellyResult:
    """Result from Kelly Criterion calculation"""

    optimal_fraction: float  # Optimal fraction to bet
    expected_growth: float  # Expected geometric growth rate
    expected_value: float  # Expected value of bet
    risk_of_ruin: float  # Probability of ruin
    adjusted_fraction: float  # Fraction adjusted for risk constraints
    recommendation: str  # Text recommendation
    confidence: float  # Confidence in recommendation


class KellyCriterion:
    """
    Kelly Criterion for Optimal Position Sizing

    The Kelly Criterion determines the optimal bet size to maximize
    long-term growth while minimizing risk of ruin.

    Key Features:
    - Full Kelly (aggressive)
    - Fractional Kelly (conservative)
    - Multi-bet scenarios
    - Confidence-based adjustment
    - Risk constraints
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Kelly Criterion calculator

        Config parameters:
        - default_method: Default Kelly method (default: HALF_KELLY)
        - max_position: Maximum position size (default: 0.20)
        - min_position: Minimum position size (default: 0.01)
        - growth_threshold: Minimum expected growth (default: 0.005)
        - ruin_threshold: Maximum acceptable ruin probability (default: 0.05)
        - volatility_penalty: Penalty for high volatility (default: 0.5)
        - confidence_weight: Weight for confidence adjustment (default: 0.3)
        """
        self.config = config or {}
        self.default_method = self.config.get("default_method", KellyMethod.HALF_KELLY)
        self.max_position = self.config.get("max_position", 0.20)
        self.min_position = self.config.get("min_position", 0.01)
        self.growth_threshold = self.config.get("growth_threshold", 0.005)
        self.ruin_threshold = self.config.get("ruin_threshold", 0.05)
        self.volatility_penalty = self.config.get("volatility_penalty", 0.5)
        self.confidence_weight = self.config.get("confidence_weight", 0.3)

        self.history: List[Dict] = []

    def calculate_kelly(
        self, params: KellyParameters, method: Optional[KellyMethod] = None
    ) -> KellyResult:
        """
        Calculate Kelly Criterion

        Args:
            params: Kelly parameters
            method: Kelly method to use (default: self.default_method)

        Returns:
            KellyResult with optimal fraction and metrics
        """
        if method is None:
            method = self.default_method

        # Calculate basic Kelly fraction
        kelly_fraction = self._calculate_basic_kelly(params)

        # Adjust for method
        adjusted_fraction = self._adjust_for_method(kelly_fraction, method)

        # Adjust for confidence
        confidence_adjusted = self._adjust_for_confidence(
            adjusted_fraction, params.confidence
        )

        # Apply risk constraints
        constrained_fraction = self._apply_constraints(confidence_adjusted)

        # Calculate metrics
        expected_growth = self._calculate_expected_growth(constrained_fraction, params)
        expected_value = self._calculate_expected_value(params)
        risk_of_ruin = self._calculate_risk_of_ruin(constrained_fraction, params)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            constrained_fraction, expected_growth, risk_of_ruin, method
        )

        result = KellyResult(
            optimal_fraction=kelly_fraction,
            expected_growth=expected_growth,
            expected_value=expected_value,
            risk_of_ruin=risk_of_ruin,
            adjusted_fraction=constrained_fraction,
            recommendation=recommendation,
            confidence=min(params.confidence, 1.0),
        )

        # Store in history
        self.history.append(
            {
                "timestamp": datetime.now(),
                "params": params,
                "result": result,
                "method": method,
            }
        )

        return result

    def _calculate_basic_kelly(self, params: KellyParameters) -> float:
        """
        Calculate basic Kelly fraction

        f* = (bp - q) / b

        Where:
        - b = avg_win / avg_loss (net odds)
        - p = win_rate
        - q = 1 - win_rate

        For trading with asymmetric wins/losses:
        f* = (p * avg_win - q * avg_loss) / (avg_win * avg_loss)
        """
        if params.avg_loss == 0:
            return 0.0

        p = params.win_rate
        q = 1.0 - p
        b = params.avg_win / params.avg_loss

        # Calculate Kelly fraction
        kelly_fraction = (b * p - q) / b

        # Adjust for volatility if available
        if params.volatility:
            volatility_adjustment = 1.0 - (self.volatility_penalty * params.volatility)
            kelly_fraction *= volatility_adjustment

        return max(0.0, kelly_fraction)

    def _adjust_for_method(self, fraction: float, method: KellyMethod) -> float:
        """Adjust fraction based on Kelly method"""
        if method == KellyMethod.FULL_KELLY:
            return fraction
        elif method == KellyMethod.HALF_KELLY:
            return fraction * 0.5
        elif method == KellyMethod.QUARTER_KELLY:
            return fraction * 0.25
        elif method == KellyMethod.FRACTIONAL_KELLY:
            # Use default fractional Kelly (half)
            return fraction * 0.5
        elif method == KellyMethod.ADAPTIVE_KELLY:
            # Adaptive: Start with half, adjust based on performance
            return self._calculate_adaptive_kelly(fraction)
        else:
            return fraction * 0.5

    def _calculate_adaptive_kelly(self, fraction: float) -> float:
        """Calculate adaptive Kelly based on historical performance"""
        if len(self.history) < 10:
            return fraction * 0.5

        # Calculate recent win rate
        recent_results = self.history[-20:]
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
        """Adjust fraction based on confidence level"""
        # Apply confidence weighting
        adjusted_fraction = fraction * (
            1.0 - self.confidence_weight * (1.0 - confidence)
        )
        return adjusted_fraction

    def _apply_constraints(self, fraction: float) -> float:
        """Apply risk constraints to fraction"""
        constrained_fraction = fraction

        # Maximum position constraint
        if constrained_fraction > self.max_position:
            constrained_fraction = self.max_position

        # Minimum position constraint
        if constrained_fraction < self.min_position and constrained_fraction > 0:
            constrained_fraction = self.min_position

        # Don't bet if expected growth is negative
        if constrained_fraction < 0:
            constrained_fraction = 0.0

        return constrained_fraction

    def _calculate_expected_growth(
        self, fraction: float, params: KellyParameters
    ) -> float:
        """
        Calculate expected geometric growth rate

        G = p * log(1 + b * f) + q * log(1 - f)

        Where:
        - p = win_rate
        - q = 1 - win_rate
        - b = avg_win / avg_loss
        - f = fraction bet
        """
        p = params.win_rate
        q = 1.0 - p
        b = params.avg_win / params.avg_loss if params.avg_loss > 0 else 1.0
        f = fraction

        # Calculate expected growth
        expected_growth = p * np.log(1 + b * f) + q * np.log(1 - f)

        return expected_growth

    def _calculate_expected_value(self, params: KellyParameters) -> float:
        """
        Calculate expected value of bet

        EV = p * avg_win - q * avg_loss
        """
        p = params.win_rate
        q = 1.0 - p

        expected_value = p * params.avg_win - q * params.avg_loss

        return expected_value

    def _calculate_risk_of_ruin(
        self, fraction: float, params: KellyParameters
    ) -> float:
        """
        Calculate approximate probability of ruin

        Risk of Ruin ≈ ((1 - b * f) / (1 + b * f))^(p / q)

        Where:
        - b = avg_win / avg_loss
        - f = fraction bet
        - p = win_rate
        - q = 1 - win_rate
        """
        if params.avg_loss == 0:
            return 0.0

        p = params.win_rate
        q = 1.0 - p
        b = params.avg_win / params.avg_loss
        f = fraction

        # Prevent division by zero or log of negative
        if 1 + b * f <= 0 or 1 - f <= 0:
            return 1.0

        try:
            base = (1 - f) / (1 + b * f)
            risk_of_ruin = base ** (p / q)
            return min(risk_of_ruin, 1.0)
        except (ZeroDivisionError, ValueError):
            return 1.0

    def _generate_recommendation(
        self,
        fraction: float,
        expected_growth: float,
        risk_of_ruin: float,
        method: KellyMethod,
    ) -> str:
        """Generate text recommendation"""
        if expected_growth < 0:
            return "AVOID - Negative expected growth"

        if risk_of_ruin > self.ruin_threshold:
            return f"AVOID - High risk of ruin ({risk_of_ruin:.2%})"

        if fraction <= 0:
            return "NO POSITION - No edge detected"

        if fraction >= self.max_position:
            return f"MAX POSITION - Strong edge ({method.value})"

        if fraction >= self.max_position * 0.75:
            return f"LARGE POSITION - Good edge ({method.value})"

        if fraction >= self.max_position * 0.5:
            return f"MEDIUM POSITION - Moderate edge ({method.value})"

        if fraction >= self.min_position:
            return f"SMALL POSITION - Weak edge ({method.value})"

        return "NO POSITION - Edge too small"

    def calculate_multi_bet_kelly(
        self, params_list: List[KellyParameters], method: Optional[KellyMethod] = None
    ) -> List[KellyResult]:
        """
        Calculate Kelly Criterion for multiple simultaneous bets

        For multiple bets, the optimal allocation is given by:
        f = C^(-1) * m

        Where:
        - C is the covariance matrix
        - m is the expected return vector

        Args:
            params_list: List of Kelly parameters for each bet
            method: Kelly method to use

        Returns:
            List of Kelly results
        """
        if not params_list:
            return []

        # For simplicity, use individual Kelly fractions
        # In practice, you'd want to account for correlation
        results = []

        for params in params_list:
            result = self.calculate_kelly(params, method)
            results.append(result)

        # Adjust for correlation (simplified)
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
        """
        Get optimal position size in monetary terms

        Args:
            account_value: Total account value
            params: Kelly parameters
            method: Kelly method

        Returns:
            Position size in currency
        """
        result = self.calculate_kelly(params, method)
        position_size = account_value * result.adjusted_fraction
        return position_size

    def get_summary_statistics(self) -> Dict:
        """Get summary statistics of Kelly calculations"""
        if not self.history:
            return {"total_calculations": 0}

        total = len(self.history)
        avg_fraction = np.mean([h["result"].adjusted_fraction for h in self.history])
        avg_growth = np.mean([h["result"].expected_growth for h in self.history])
        avg_risk = np.mean([h["result"].risk_of_ruin for h in self.history])

        positive_growth = sum(
            1 for h in self.history if h["result"].expected_growth > 0
        )

        return {
            "total_calculations": total,
            "average_fraction": round(avg_fraction, 4),
            "average_expected_growth": round(avg_growth, 6),
            "average_risk_of_ruin": round(avg_risk, 4),
            "positive_growth_rate": round(positive_growth / total, 4),
            "total_capital_at_risk": round(avg_fraction * 100, 2),
        }


def calculate_kelly_position(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    account_value: float = 100000,
    method: Optional[KellyMethod] = None,
    config: Optional[Dict] = None,
) -> KellyResult:
    """
    Convenience function to calculate Kelly position size

    Args:
        win_rate: Probability of winning (0-1)
        avg_win: Average win amount
        avg_loss: Average loss amount
        account_value: Account value (default: 100000)
        method: Kelly method
        config: Configuration dictionary

    Returns:
        KellyResult with optimal fraction and metrics
    """
    kelly = KellyCriterion(config)

    params = KellyParameters(
        win_rate=win_rate, avg_win=avg_win, avg_loss=avg_loss, confidence=0.7
    )

    return kelly.calculate_kelly(params, method)


def main():
    """Example usage"""
    kelly = KellyCriterion()

    # Example: Trading strategy with 55% win rate
    params = KellyParameters(win_rate=0.55, avg_win=200, avg_loss=150, confidence=0.75)

    result = kelly.calculate_kelly(params, KellyMethod.HALF_KELLY)

    print("Kelly Criterion Analysis")
    print("=" * 40)
    print(
        f"Optimal Fraction: {result.optimal_fraction:.4f} ({result.optimal_fraction * 100:.2f}%)"
    )
    print(
        f"Adjusted Fraction: {result.adjusted_fraction:.4f} ({result.adjusted_fraction * 100:.2f}%)"
    )
    print(f"Expected Growth: {result.expected_growth:.6f}")
    print(f"Expected Value: {result.expected_value:.2f}")
    print(f"Risk of Ruin: {result.risk_of_ruin:.4%}")
    print(f"Recommendation: {result.recommendation}")

    # Calculate position size
    account_value = 100000
    position_size = kelly.get_optimal_position_size(account_value, params)
    print(f"\nPosition Size for ${account_value:,} account: ${position_size:,.2f}")

    # Get summary statistics
    stats = kelly.get_summary_statistics()
    print(f"\nSummary Statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
