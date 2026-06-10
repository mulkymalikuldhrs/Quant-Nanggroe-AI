"""
Market Regime Detection Engine
================================
From Quant-Nanggroe-AI — Probabilistic regime identification via Hidden Markov Models.

Detects and classifies market regimes in real-time:
  - Bull: Sustained uptrend with moderate volatility
  - Bear: Sustained downtrend with elevated volatility
  - Sideways: Range-bound with low volatility
  - Volatile: High volatility with no clear directional bias

Features:
  - Hidden Markov Model (HMM) for regime identification
  - Regime transition probability matrix
  - Real-time regime detection from price data
  - Integration with market_state.py for deterministic cross-validation
  - Fallback to simplified detection when hmmlearn unavailable

The HMM approach models regime as a latent state variable that follows
a Markov chain, with observed returns emitted from regime-specific
distributions. This provides probabilistic regime assignments rather
than hard thresholds.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from quant_nanggroe_ai.exceptions import InsufficientDataError, InvalidParameterError
from quant_nanggroe_ai.logging import get_logger
from quant_nanggroe_ai.types import MarketRegime

logger = get_logger(__name__)

# Try importing hmmlearn — graceful fallback if unavailable
try:
    from hmmlearn.hmm import GaussianHMM

    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logger.warning("hmmlearn_not_available", message="Falling back to simplified regime detection")


# ══════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════


class RegimeClassification(str, object):
    """Regime classification labels for HMM states."""

    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    VOLATILE = "VOLATILE"


class RegimeProbability(BaseModel):
    """Probability distribution over regime states."""

    bull: float = Field(ge=0.0, le=1.0, default=0.25)
    bear: float = Field(ge=0.0, le=1.0, default=0.25)
    sideways: float = Field(ge=0.0, le=1.0, default=0.25)
    volatile: float = Field(ge=0.0, le=1.0, default=0.25)


class RegimeDetectionResult(BaseModel):
    """Result of regime detection from price data."""

    current_regime: str = RegimeClassification.SIDEWAYS
    regime_probability: RegimeProbability = Field(default_factory=RegimeProbability)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    transition_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    regime_history: list[str] = Field(
        default_factory=list,
        description="Recent regime sequence",
    )
    duration_in_regime: int = Field(
        default=0,
        description="Number of periods in current regime",
    )
    likely_transition: str | None = Field(
        default=None,
        description="Most likely next regime transition",
    )
    market_regime_enum: MarketRegime = MarketRegime.UNKNOWN
    method: str = "HMM"
    timestamp: datetime = Field(default_factory=datetime.now)


class HMMConfig(BaseModel):
    """Configuration for the Hidden Markov Model."""

    n_components: int = Field(
        default=4,
        ge=2,
        le=8,
        description="Number of hidden states (regimes)",
    )
    covariance_type: str = Field(
        default="full",
        description="Covariance type: full, diag, spherical, tied",
    )
    n_iter: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum EM iterations",
    )
    tol: float = Field(
        default=1e-4,
        gt=0,
        description="Convergence threshold",
    )
    random_state: int = Field(
        default=42,
        description="Random seed for reproducibility",
    )
    min_observations: int = Field(
        default=50,
        ge=20,
        description="Minimum observations needed to fit HMM",
    )
    lookback_window: int = Field(
        default=252,
        ge=50,
        le=1000,
        description="Lookback window for real-time detection",
    )


class RegimeTransitionMatrix(BaseModel):
    """Regime transition probability matrix."""

    matrix: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "BULL": {"BULL": 0.85, "BEAR": 0.05, "SIDEWAYS": 0.07, "VOLATILE": 0.03},
            "BEAR": {"BEAR": 0.80, "BULL": 0.05, "SIDEWAYS": 0.10, "VOLATILE": 0.05},
            "SIDEWAYS": {"SIDEWAYS": 0.70, "BULL": 0.12, "BEAR": 0.10, "VOLATILE": 0.08},
            "VOLATILE": {"VOLATILE": 0.55, "BULL": 0.15, "BEAR": 0.15, "SIDEWAYS": 0.15},
        },
        description="Transition probability matrix P(j|i) = P(regime_t=j | regime_{t-1}=i)",
    )


# ══════════════════════════════════════════════════════════════════════
# REGIME DETECTION ENGINE
# ══════════════════════════════════════════════════════════════════════


class RegimeDetectionEngine:
    """
    Market regime detection using Hidden Markov Models.

    The engine identifies market regimes by fitting a Gaussian HMM to
    observed return distributions. Each hidden state corresponds to a
    regime (Bull, Bear, Sideways, Volatile), characterized by distinct
    mean and variance of returns.

    Features:
    - HMM-based probabilistic regime identification
    - Regime transition probability estimation
    - Real-time regime detection from streaming price data
    - Integration with market_state.py for cross-validation
    - Fallback to statistical threshold detection when hmmlearn unavailable
    - Configurable model parameters

    Regime mapping from HMM states:
    - Bull: Positive mean, low-to-moderate variance
    - Bear: Negative mean, high variance
    - Sideways: Near-zero mean, low variance
    - Volatile: Any mean, very high variance

    Example:
        engine = RegimeDetectionEngine()
        engine.fit(daily_returns=[0.01, -0.02, 0.005, ...])
        result = engine.detect_current_regime()
        print(result.current_regime)  # "BULL"
        print(result.regime_probability.bull)  # 0.72
    """

    # Thresholds for fallback regime classification
    BULL_DRIFT_THRESHOLD = 0.0003  # ~7.5% annualized
    BEAR_DRIFT_THRESHOLD = -0.0003  # ~-7.5% annualized
    HIGH_VOL_THRESHOLD = 0.015  # ~24% annualized
    LOW_VOL_THRESHOLD = 0.005  # ~8% annualized

    def __init__(self, config: HMMConfig | None = None) -> None:
        """
        Initialize the regime detection engine.

        Args:
            config: HMM configuration. Uses defaults if not provided.
        """
        self._config = config or HMMConfig()
        self._hmm_model: Any = None  # GaussianHMM or None
        self._is_fitted = False
        self._transition_matrix = RegimeTransitionMatrix()
        self._regime_mapping: dict[int, str] = {}  # HMM state -> regime name
        self._last_result: RegimeDetectionResult | None = None
        self._recent_returns: list[float] = []
        self._regime_history: list[str] = []

    @property
    def is_fitted(self) -> bool:
        """Whether the HMM model has been fitted."""
        return self._is_fitted

    @property
    def hmm_available(self) -> bool:
        """Whether hmmlearn is available for HMM-based detection."""
        return HMM_AVAILABLE

    @property
    def transition_matrix(self) -> RegimeTransitionMatrix:
        """Get current transition probability matrix."""
        return self._transition_matrix

    # ══════════════════════════════════════════════════════════════════
    # Model Fitting
    # ══════════════════════════════════════════════════════════════════

    def fit(self, daily_returns: list[float]) -> dict[str, Any]:
        """
        Fit the Hidden Markov Model to historical returns.

        The HMM learns:
        - Regime-specific return distributions (mean, variance)
        - Transition probabilities between regimes
        - Initial state distribution

        After fitting, each hidden state is mapped to a regime label
        based on its estimated mean and variance.

        Args:
            daily_returns: Historical daily returns (at least min_observations)

        Returns:
            Dict with fitting summary

        Raises:
            InsufficientDataError: If not enough observations provided
        """
        n = len(daily_returns)
        if n < self._config.min_observations:
            raise InsufficientDataError(
                required=self._config.min_observations,
                actual=n,
                indicator="regime_hmm_fit",
            )

        self._recent_returns = daily_returns[-self._config.lookback_window:]

        if HMM_AVAILABLE:
            return self._fit_hmm(daily_returns)
        else:
            return self._fit_fallback(daily_returns)

    def _fit_hmm(self, daily_returns: list[float]) -> dict[str, Any]:
        """Fit Gaussian HMM to returns data."""
        returns_arr = np.array(daily_returns).reshape(-1, 1)

        # Create and fit the HMM
        model = GaussianHMM(
            n_components=self._config.n_components,
            covariance_type=self._config.covariance_type,
            n_iter=self._config.n_iter,
            tol=self._config.tol,
            random_state=self._config.random_state,
        )

        try:
            model.fit(returns_arr)
            self._hmm_model = model
            self._is_fitted = True

            # Map HMM states to regime names based on learned parameters
            self._map_hmm_states(model)

            # Update transition matrix from HMM
            self._update_transition_matrix(model)

            logger.info(
                "hmm_fit_success",
                n_components=self._config.n_components,
                n_observations=len(daily_returns),
                convergence=model.monitor_.converged if hasattr(model, "monitor_") else True,
            )

            return {
                "status": "FITTED",
                "method": "HMM",
                "n_components": self._config.n_components,
                "n_observations": len(daily_returns),
                "regime_mapping": self._regime_mapping,
                "means": {str(k): float(v) for k, v in enumerate(model.means_.flatten())},
            }

        except Exception as e:
            logger.warning("hmm_fit_failed", error=str(e), fallback="statistical")
            return self._fit_fallback(daily_returns)

    def _fit_fallback(self, daily_returns: list[float]) -> dict[str, Any]:
        """
        Fallback regime fitting using statistical thresholds.

        Used when hmmlearn is unavailable or HMM fitting fails.
        Classifies the overall data into a single regime and uses
        default transition probabilities.
        """
        arr = np.array(daily_returns)
        mean_return = float(np.mean(arr))
        std_return = float(np.std(arr, ddof=1))

        # Classify current data into a regime
        regime = self._classify_by_thresholds(mean_return, std_return)

        self._is_fitted = True
        self._hmm_model = None  # No HMM model available

        # Use default regime mapping (identity)
        self._regime_mapping = {
            0: "BULL",
            1: "BEAR",
            2: "SIDEWAYS",
            3: "VOLATILE",
        }

        logger.info(
            "fallback_fit_success",
            mean_return=round(mean_return, 6),
            std_return=round(std_return, 6),
            regime=regime,
        )

        return {
            "status": "FITTED",
            "method": "STATISTICAL_FALLBACK",
            "n_observations": len(daily_returns),
            "mean_return": round(mean_return, 6),
            "std_return": round(std_return, 6),
            "classified_regime": regime,
        }

    # ══════════════════════════════════════════════════════════════════
    # Real-Time Detection
    # ══════════════════════════════════════════════════════════════════

    def detect_current_regime(
        self,
        recent_returns: list[float] | None = None,
    ) -> RegimeDetectionResult:
        """
        Detect current market regime from recent returns.

        Uses the fitted HMM model for probabilistic regime assignment,
        or falls back to statistical threshold classification.

        Args:
            recent_returns: Override returns for detection. Uses stored
                returns if not provided.

        Returns:
            RegimeDetectionResult with current regime, probabilities,
            and transition information.
        """
        if recent_returns is not None:
            self._recent_returns = recent_returns

        if not self._recent_returns:
            return RegimeDetectionResult(
                current_regime=RegimeClassification.SIDEWAYS,
                regime_probability=RegimeProbability(),
                confidence=0.0,
                method="NO_DATA",
            )

        if HMM_AVAILABLE and self._hmm_model is not None:
            result = self._detect_hmm()
        else:
            result = self._detect_statistical()

        # Update regime history
        self._regime_history.append(result.current_regime)
        if len(self._regime_history) > 100:
            self._regime_history = self._regime_history[-100:]

        # Compute duration in current regime
        result.duration_in_regime = self._compute_regime_duration(result.current_regime)

        # Find most likely transition
        result.likely_transition = self._find_likely_transition(result.current_regime)

        # Map to MarketRegime enum for integration
        result.market_regime_enum = self._to_market_regime(result.current_regime)

        # Set transition matrix
        result.transition_matrix = self._transition_matrix.matrix

        self._last_result = result
        return result

    def detect_from_prices(
        self,
        prices: list[float],
    ) -> RegimeDetectionResult:
        """
        Detect regime directly from price data.

        Converts prices to returns and runs detection.

        Args:
            prices: Price series (at least 2 data points)

        Returns:
            RegimeDetectionResult with detected regime

        Raises:
            InsufficientDataError: If less than 2 prices provided
        """
        if len(prices) < 2:
            raise InsufficientDataError(
                required=2,
                actual=len(prices),
                indicator="regime_detection_from_prices",
            )

        # Compute log returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0 and prices[i] > 0:
                returns.append(math.log(prices[i] / prices[i - 1]))
            else:
                returns.append(0.0)

        # Auto-fit if not fitted
        if not self._is_fitted and len(returns) >= self._config.min_observations:
            self.fit(returns)

        return self.detect_current_regime(returns)

    def _detect_hmm(self) -> RegimeDetectionResult:
        """Detect regime using fitted HMM model."""
        if self._hmm_model is None:
            return self._detect_statistical()

        returns_arr = np.array(self._recent_returns).reshape(-1, 1)

        try:
            # Get posterior probabilities for each state
            posterior_probs = self._hmm_model.predict_proba(returns_arr)
            last_probs = posterior_probs[-1]

            # Map to regime names
            regime_probs = RegimeProbability()
            for state_idx, prob in enumerate(last_probs):
                regime_name = self._regime_mapping.get(state_idx, "SIDEWAYS")
                prob_val = float(prob)
                if regime_name == "BULL":
                    regime_probs.bull = prob_val
                elif regime_name == "BEAR":
                    regime_probs.bear = prob_val
                elif regime_name == "SIDEWAYS":
                    regime_probs.sideways = prob_val
                elif regime_name == "VOLATILE":
                    regime_probs.volatile = prob_val

            # Most likely regime
            most_likely_state = int(np.argmax(last_probs))
            current_regime = self._regime_mapping.get(most_likely_state, "SIDEWAYS")
            confidence = float(last_probs[most_likely_state])

            return RegimeDetectionResult(
                current_regime=current_regime,
                regime_probability=regime_probs,
                confidence=round(confidence, 4),
                regime_history=self._regime_history[-20:],
                method="HMM",
            )

        except Exception as e:
            logger.warning("hmm_detect_failed", error=str(e), fallback="statistical")
            return self._detect_statistical()

    def _detect_statistical(self) -> RegimeDetectionResult:
        """
        Fallback regime detection using statistical thresholds.

        Classifies the current regime based on the mean and standard
        deviation of recent returns using fixed thresholds.
        """
        if not self._recent_returns:
            return RegimeDetectionResult(
                current_regime=RegimeClassification.SIDEWAYS,
                regime_probability=RegimeProbability(),
                confidence=0.0,
                method="STATISTICAL_FALLBACK",
            )

        arr = np.array(self._recent_returns)
        mean_return = float(np.mean(arr))
        std_return = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0

        regime = self._classify_by_thresholds(mean_return, std_return)

        # Estimate probabilities from recent classification
        regime_probs = self._estimate_probabilities(mean_return, std_return)

        # Confidence based on how clear the classification is
        max_prob = max(
            regime_probs.bull, regime_probs.bear,
            regime_probs.sideways, regime_probs.volatile,
        )
        confidence = min(1.0, max_prob * 1.2)  # Scale up slightly

        return RegimeDetectionResult(
            current_regime=regime,
            regime_probability=regime_probs,
            confidence=round(confidence, 4),
            regime_history=self._regime_history[-20:],
            method="STATISTICAL_FALLBACK",
        )

    # ══════════════════════════════════════════════════════════════════
    # Integration with MarketStateEngine
    # ══════════════════════════════════════════════════════════════════

    def cross_validate_with_market_state(
        self,
        market_state_regime: MarketRegime,
    ) -> dict[str, Any]:
        """
        Cross-validate HMM regime detection with deterministic market state engine.

        Compares the probabilistic HMM classification with the deterministic
        market_state.py classification. Disagreements are logged for review.

        Args:
            market_state_regime: Regime from MarketStateEngine

        Returns:
            Dict with comparison results
        """
        if self._last_result is None:
            return {"status": "NO_HMM_RESULT", "market_state": market_state_regime.value}

        hmm_regime = self._last_result.current_regime
        market_regime = self._to_hmm_regime_label(market_state_regime)

        agrees = hmm_regime == market_regime

        result = {
            "hmm_regime": hmm_regime,
            "market_state_regime": market_regime,
            "agrees": agrees,
            "hmm_confidence": self._last_result.confidence,
            "hmm_method": self._last_result.method,
        }

        if not agrees:
            logger.info(
                "regime_disagreement",
                hmm_regime=hmm_regime,
                market_state_regime=market_regime,
                hmm_confidence=self._last_result.confidence,
            )

        return result

    # ══════════════════════════════════════════════════════════════════
    # Helper Methods
    # ══════════════════════════════════════════════════════════════════

    def _map_hmm_states(self, model: Any) -> None:
        """
        Map HMM hidden states to regime labels.

        The mapping is based on the learned mean and variance of each state:
        - Bull: highest mean, moderate variance
        - Bear: lowest mean, high variance
        - Volatile: highest variance
        - Sideways: near-zero mean, low variance
        """
        means = model.means_.flatten()
        n_states = len(means)

        # Get variances from covariances
        if self._config.covariance_type == "full":
            variances = np.array([model.covars_[i][0, 0] for i in range(n_states)])
        elif self._config.covariance_type == "diag":
            variances = np.array([model.covars_[i][0] for i in range(n_states)])
        else:
            variances = np.array([model.covars_[i] for i in range(n_states)])

        # Sort states by mean return (ascending)
        sorted_by_mean = sorted(range(n_states), key=lambda i: means[i])

        self._regime_mapping = {}

        if n_states == 2:
            # Simple bull/bear split
            self._regime_mapping[sorted_by_mean[0]] = "BEAR"
            self._regime_mapping[sorted_by_mean[1]] = "BULL"
        elif n_states == 3:
            self._regime_mapping[sorted_by_mean[0]] = "BEAR"
            # Middle state: check variance
            mid = sorted_by_mean[1]
            if variances[mid] > np.median(variances):
                self._regime_mapping[mid] = "VOLATILE"
            else:
                self._regime_mapping[mid] = "SIDEWAYS"
            self._regime_mapping[sorted_by_mean[2]] = "BULL"
        else:
            # 4+ states: map to our 4 regime types
            # Highest variance -> VOLATILE
            volatile_state = int(np.argmax(variances))

            # Remaining states sorted by mean
            remaining = [i for i in range(n_states) if i != volatile_state]
            remaining_sorted = sorted(remaining, key=lambda i: means[i])

            self._regime_mapping[volatile_state] = "VOLATILE"
            if len(remaining_sorted) >= 3:
                self._regime_mapping[remaining_sorted[0]] = "BEAR"
                self._regime_mapping[remaining_sorted[-1]] = "BULL"
                # Middle states -> SIDEWAYS
                for mid_state in remaining_sorted[1:-1]:
                    self._regime_mapping[mid_state] = "SIDEWAYS"
            elif len(remaining_sorted) == 2:
                self._regime_mapping[remaining_sorted[0]] = "BEAR"
                self._regime_mapping[remaining_sorted[1]] = "BULL"
            elif len(remaining_sorted) == 1:
                if means[remaining_sorted[0]] > 0:
                    self._regime_mapping[remaining_sorted[0]] = "BULL"
                else:
                    self._regime_mapping[remaining_sorted[0]] = "BEAR"

        # Fill any unmapped states
        default_regimes = ["SIDEWAYS", "VOLATILE"]
        for i in range(n_states):
            if i not in self._regime_mapping:
                self._regime_mapping[i] = default_regimes[i % len(default_regimes)]

    def _update_transition_matrix(self, model: Any) -> None:
        """Update transition matrix from HMM learned parameters."""
        try:
            trans_mat = model.transmat_
            n_states = trans_mat.shape[0]

            matrix: dict[str, dict[str, float]] = {}
            for i in range(n_states):
                from_regime = self._regime_mapping.get(i, "SIDEWAYS")
                matrix[from_regime] = {}
                for j in range(n_states):
                    to_regime = self._regime_mapping.get(j, "SIDEWAYS")
                    matrix[from_regime][to_regime] = round(float(trans_mat[i, j]), 4)

            self._transition_matrix = RegimeTransitionMatrix(matrix=matrix)

        except Exception as e:
            logger.warning("transition_matrix_update_failed", error=str(e))

    @staticmethod
    def _classify_by_thresholds(mean_return: float, std_return: float) -> str:
        """
        Classify regime using fixed statistical thresholds.

        Args:
            mean_return: Mean daily return
            std_return: Standard deviation of daily returns

        Returns:
            Regime string: BULL, BEAR, SIDEWAYS, or VOLATILE
        """
        if std_return > 0.02:  # Very high volatility
            return RegimeClassification.VOLATILE
        elif mean_return > 0.0005 and std_return < 0.015:
            return RegimeClassification.BULL
        elif mean_return < -0.0005:
            return RegimeClassification.BEAR
        elif std_return < 0.008:
            return RegimeClassification.SIDEWAYS
        elif mean_return > 0.0003:
            return RegimeClassification.BULL
        elif mean_return < -0.0003:
            return RegimeClassification.BEAR
        else:
            return RegimeClassification.SIDEWAYS

    @staticmethod
    def _estimate_probabilities(mean_return: float, std_return: float) -> RegimeProbability:
        """
        Estimate regime probabilities from return statistics.

        Uses a soft classification approach where each regime's probability
        is proportional to how well the statistics match the regime profile.
        """
        # Regime profiles: (mean_target, vol_target)
        profiles = {
            "bull": (0.001, 0.010),      # Positive drift, moderate vol
            "bear": (-0.001, 0.015),     # Negative drift, higher vol
            "sideways": (0.0, 0.006),    # Near-zero drift, low vol
            "volatile": (0.0, 0.025),    # Any drift, very high vol
        }

        scores: dict[str, float] = {}
        for regime, (target_mean, target_vol) in profiles.items():
            # Score based on distance from ideal profile
            mean_dist = abs(mean_return - target_mean)
            vol_dist = abs(std_return - target_vol)
            # Lower distance = higher score (using Gaussian-like kernel)
            score = math.exp(-mean_dist ** 2 / 0.0002) * math.exp(-vol_dist ** 2 / 0.0004)
            scores[regime] = score

        # Normalize to probabilities
        total = sum(scores.values()) or 1.0
        return RegimeProbability(
            bull=round(scores["bull"] / total, 4),
            bear=round(scores["bear"] / total, 4),
            sideways=round(scores["sideways"] / total, 4),
            volatile=round(scores["volatile"] / total, 4),
        )

    def _compute_regime_duration(self, current_regime: str) -> int:
        """Compute the number of consecutive periods in the current regime."""
        duration = 0
        for regime in reversed(self._regime_history):
            if regime == current_regime:
                duration += 1
            else:
                break
        return duration

    def _find_likely_transition(self, current_regime: str) -> str | None:
        """Find the most likely next regime transition from current regime."""
        transitions = self._transition_matrix.matrix.get(current_regime, {})
        if not transitions:
            return None

        # Find highest probability transition to a different regime
        best_target = None
        best_prob = 0.0
        for target, prob in transitions.items():
            if target != current_regime and prob > best_prob:
                best_target = target
                best_prob = prob

        return best_target

    @staticmethod
    def _to_market_regime(hmm_regime: str) -> MarketRegime:
        """Map HMM regime label to MarketRegime enum."""
        mapping = {
            "BULL": MarketRegime.TRENDING_UP,
            "BEAR": MarketRegime.TRENDING_DOWN,
            "SIDEWAYS": MarketRegime.RANGE,
            "VOLATILE": MarketRegime.VOLATILE,
        }
        return mapping.get(hmm_regime, MarketRegime.UNKNOWN)

    @staticmethod
    def _to_hmm_regime_label(market_regime: MarketRegime) -> str:
        """Map MarketRegime enum to HMM regime label."""
        mapping = {
            MarketRegime.TRENDING_UP: "BULL",
            MarketRegime.TRENDING_DOWN: "BEAR",
            MarketRegime.RANGE: "SIDEWAYS",
            MarketRegime.CALM: "SIDEWAYS",
            MarketRegime.VOLATILE: "VOLATILE",
            MarketRegime.PANIC: "VOLATILE",
            MarketRegime.RISK_OFF: "BEAR",
            MarketRegime.TRENDING: "BULL",  # Default trending to bull
            MarketRegime.MEAN_REVERT: "SIDEWAYS",
        }
        return mapping.get(market_regime, "SIDEWAYS")

    def status(self) -> dict[str, Any]:
        """Get current regime detection engine status."""
        return {
            "is_fitted": self._is_fitted,
            "hmm_available": HMM_AVAILABLE,
            "hmm_model_active": self._hmm_model is not None,
            "n_regime_states": self._config.n_components,
            "regime_mapping": self._regime_mapping,
            "regime_history_length": len(self._regime_history),
            "last_regime": self._last_result.current_regime if self._last_result else None,
            "last_confidence": self._last_result.confidence if self._last_result else None,
            "transition_matrix": self._transition_matrix.matrix,
            "timestamp": datetime.now().isoformat(),
        }
