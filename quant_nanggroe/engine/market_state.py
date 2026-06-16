"""Market regime detection for the AI-MultiColony finance module.

Detects the current market regime (trending, ranging, volatile,
crisis) using statistical analysis of price and volume data.

Regime detection is crucial for strategy selection and risk
management – different strategies perform optimally in different
market conditions.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class MarketRegime(str, Enum):
    """Detected market regime."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"


class RegimeConfidence(str, Enum):
    """Confidence level of regime detection."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Models ───────────────────────────────────────────────────────────────────


class RegimeResult(BaseModel):
    """Result from a regime detection analysis."""
    model_config = ConfigDict(frozen=False)

    result_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    regime: MarketRegime = MarketRegime.UNKNOWN
    confidence: float = 0.0
    confidence_level: RegimeConfidence = RegimeConfidence.LOW
    indicators: Dict[str, float] = Field(default_factory=dict)
    transition_probability: Dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str = ""

    @property
    def is_stressed(self) -> bool:
        """True if market is in a stressed regime."""
        return self.regime in (MarketRegime.VOLATILE, MarketRegime.CRISIS)


class RegimeConfig(BaseModel):
    """Configuration for regime detection."""
    model_config = ConfigDict(frozen=False)

    lookback_period: int = 50        # Bars for statistical analysis
    trend_threshold: float = 0.02    # 2% slope threshold for trend detection
    volatility_threshold: float = 0.03  # 3% std dev threshold for volatility
    crisis_threshold: float = 0.05   # 5% daily move for crisis detection
    adx_trend_threshold: float = 25.0  # ADX above 25 indicates trend
    adx_range_threshold: float = 20.0   # ADX below 20 indicates range
    smoothing_factor: float = 0.1    # EMA smoothing


# ── Regime Detector ──────────────────────────────────────────────────────────


class MarketRegimeDetector:
    """Detects the current market regime from price data.

    Uses a combination of statistical indicators:
    * Price trend (linear regression slope)
    * Volatility (standard deviation of returns)
    * Average Directional Index (ADX) approximation
    * Volume profile analysis

    Usage::

        detector = MarketRegimeDetector()
        result = detector.detect(closes=[100, 101, 102, ...], volumes=[...])
        print(result.regime, result.confidence)
    """

    def __init__(self, config: Optional[RegimeConfig] = None):
        self._config = config or RegimeConfig()
        self._history: List[RegimeResult] = []

    def detect(
        self,
        closes: List[float],
        volumes: Optional[List[float]] = None,
        symbol: str = "",
    ) -> RegimeResult:
        """Detect the current market regime from price data.

        Parameters
        ----------
        closes:
            List of closing prices (most recent last).
        volumes:
            Optional list of volume data.
        symbol:
            Symbol being analyzed.

        Returns
        -------
        RegimeResult
            Detected regime with confidence and indicators.
        """
        if len(closes) < 10:
            return RegimeResult(
                regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                confidence_level=RegimeConfidence.LOW,
                symbol=symbol,
            )

        # Calculate indicators
        returns = self._compute_returns(closes)
        slope = self._compute_slope(closes)
        volatility = self._compute_volatility(returns)
        adx = self._compute_adx_approx(closes)
        max_daily_move = self._compute_max_daily_move(returns)

        indicators = {
            "slope": round(slope, 6),
            "volatility": round(volatility, 4),
            "adx": round(adx, 2),
            "max_daily_move": round(max_daily_move, 4),
        }

        # Volume analysis (if available)
        if volumes and len(volumes) >= 10:
            vol_ratio = self._compute_volume_ratio(volumes)
            indicators["volume_ratio"] = round(vol_ratio, 2)

        # Regime classification
        regime, confidence = self._classify_regime(
            slope=slope,
            volatility=volatility,
            adx=adx,
            max_daily_move=max_daily_move,
        )

        # Determine confidence level
        if confidence >= 0.8:
            conf_level = RegimeConfidence.HIGH
        elif confidence >= 0.5:
            conf_level = RegimeConfidence.MEDIUM
        else:
            conf_level = RegimeConfidence.LOW

        # Compute transition probabilities
        transitions = self._compute_transitions(regime, indicators)

        result = RegimeResult(
            regime=regime,
            confidence=round(confidence, 3),
            confidence_level=conf_level,
            indicators=indicators,
            transition_probability=transitions,
            symbol=symbol,
        )

        self._history.append(result)
        return result

    def _classify_regime(
        self,
        slope: float,
        volatility: float,
        adx: float,
        max_daily_move: float,
    ) -> Tuple[MarketRegime, float]:
        """Classify the market regime based on indicators."""
        confidence = 0.5

        # Crisis detection (highest priority)
        if max_daily_move > self._config.crisis_threshold:
            return MarketRegime.CRISIS, 0.9

        # High volatility
        if volatility > self._config.volatility_threshold:
            confidence = 0.7 + min(0.2, (volatility - self._config.volatility_threshold) * 5)
            return MarketRegime.VOLATILE, min(0.95, confidence)

        # Trending (up or down)
        if abs(slope) > self._config.trend_threshold and adx > self._config.adx_trend_threshold:
            regime = MarketRegime.TRENDING_UP if slope > 0 else MarketRegime.TRENDING_DOWN
            confidence = 0.6 + min(0.3, (adx - self._config.adx_trend_threshold) / 50)
            return regime, min(0.95, confidence)

        # Ranging
        if adx < self._config.adx_range_threshold and abs(slope) < self._config.trend_threshold:
            confidence = 0.6 + min(0.3, (self._config.adx_range_threshold - adx) / 20)
            return MarketRegime.RANGING, min(0.95, confidence)

        # Default: trending direction based on slope
        if slope > 0:
            return MarketRegime.TRENDING_UP, 0.4
        elif slope < 0:
            return MarketRegime.TRENDING_DOWN, 0.4
        else:
            return MarketRegime.RANGING, 0.4

    def _compute_transitions(
        self,
        current: MarketRegime,
        indicators: Dict[str, float],
    ) -> Dict[str, float]:
        """Compute rough transition probabilities to other regimes."""
        transitions: Dict[str, float] = {}
        volatility = indicators.get("volatility", 0.01)
        slope = indicators.get("slope", 0.0)

        # Base probabilities based on current regime
        if current == MarketRegime.TRENDING_UP:
            transitions = {
                MarketRegime.TRENDING_UP.value: 0.6,
                MarketRegime.RANGING.value: 0.2,
                MarketRegime.VOLATILE.value: 0.1,
                MarketRegime.TRENDING_DOWN.value: 0.1,
            }
        elif current == MarketRegime.TRENDING_DOWN:
            transitions = {
                MarketRegime.TRENDING_DOWN.value: 0.5,
                MarketRegime.RANGING.value: 0.2,
                MarketRegime.VOLATILE.value: 0.2,
                MarketRegime.CRISIS.value: 0.1,
            }
        elif current == MarketRegime.RANGING:
            transitions = {
                MarketRegime.RANGING.value: 0.5,
                MarketRegime.TRENDING_UP.value: 0.2,
                MarketRegime.TRENDING_DOWN.value: 0.2,
                MarketRegime.VOLATILE.value: 0.1,
            }
        elif current == MarketRegime.VOLATILE:
            transitions = {
                MarketRegime.VOLATILE.value: 0.3,
                MarketRegime.CRISIS.value: 0.2,
                MarketRegime.TRENDING_DOWN.value: 0.2,
                MarketRegime.RANGING.value: 0.2,
                MarketRegime.RECOVERY.value: 0.1,
            }
        elif current == MarketRegime.CRISIS:
            transitions = {
                MarketRegime.CRISIS.value: 0.3,
                MarketRegime.VOLATILE.value: 0.3,
                MarketRegime.RECOVERY.value: 0.3,
                MarketRegime.TRENDING_DOWN.value: 0.1,
            }
        else:
            transitions = {MarketRegime.UNKNOWN.value: 0.5, MarketRegime.RANGING.value: 0.5}

        return transitions

    # ── Statistical computations ────────────────────────────────────────

    @staticmethod
    def _compute_returns(closes: List[float]) -> List[float]:
        """Compute daily returns from closing prices."""
        returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
            else:
                returns.append(0.0)
        return returns

    @staticmethod
    def _compute_slope(prices: List[float]) -> float:
        """Compute linear regression slope of prices."""
        n = len(prices)
        if n < 2:
            return 0.0
        x_avg = (n - 1) / 2.0
        y_avg = sum(prices) / n
        numerator = sum((i - x_avg) * (p - y_avg) for i, p in enumerate(prices))
        denominator = sum((i - x_avg) ** 2 for i in range(n))
        if denominator == 0 or y_avg == 0:
            return 0.0
        return (numerator / denominator) / y_avg  # Normalized slope

    @staticmethod
    def _compute_volatility(returns: List[float]) -> float:
        """Compute standard deviation of returns (volatility)."""
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance)

    @staticmethod
    def _compute_adx_approx(closes: List[float]) -> float:
        """Compute a simplified ADX approximation.

        Real ADX is complex; this approximation uses directional
        movement ratio over the lookback period.
        """
        if len(closes) < 3:
            return 0.0

        up_moves = 0.0
        down_moves = 0.0

        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            if change > 0:
                up_moves += change
            else:
                down_moves += abs(change)

        total = up_moves + down_moves
        if total == 0:
            return 0.0

        dx = abs(up_moves - down_moves) / total * 100
        return min(100.0, dx)

    @staticmethod
    def _compute_max_daily_move(returns: List[float]) -> float:
        """Compute the maximum absolute daily return."""
        if not returns:
            return 0.0
        return max(abs(r) for r in returns)

    @staticmethod
    def _compute_volume_ratio(volumes: List[float]) -> float:
        """Compute recent vs. average volume ratio."""
        if len(volumes) < 10:
            return 1.0
        recent = sum(volumes[-5:]) / 5
        average = sum(volumes) / len(volumes)
        if average == 0:
            return 1.0
        return recent / average

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def history(self) -> List[RegimeResult]:
        return list(self._history)

    @property
    def current_regime(self) -> Optional[MarketRegime]:
        """Most recently detected regime."""
        if self._history:
            return self._history[-1].regime
        return None

    @property
    def config(self) -> RegimeConfig:
        return self._config

    @property
    def stats(self) -> Dict[str, Any]:
        """Detector statistics."""
        regime_counts: Dict[str, int] = {}
        for result in self._history:
            key = result.regime.value
            regime_counts[key] = regime_counts.get(key, 0) + 1

        return {
            "detections": len(self._history),
            "regime_distribution": regime_counts,
            "current_regime": self.current_regime.value if self.current_regime else None,
        }
