"""
Market regime detection for the AI-MultiColony finance module.

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

from pydantic import BaseModel, ConfigDict, Field

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


from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from quant_nanggroe.types.engine import (
    MarketRegime as TypesMarketRegime,
    VolatilityLevel,
    LiquidityLevel,
    MarketState,
)


# ── MarketStateResult ───────────────────────────────────────────────────────


@dataclass
class MarketStateResult:
    """Result from a market state / regime detection run.

    Attributes
    ----------
    base_regime:
        The raw detected regime before overrides.
    regime:
        The final regime after applying overrides (PANIC → NO_TRADE, etc.).
    trade_allowed:
        Whether trading is permitted in this regime.
    no_trade_reasons:
        Reasons why trading is blocked (if applicable).
    volatility:
        Volatility classification.
    liquidity:
        Liquidity classification.
    inputs:
        Dict of the input values used for detection.
    symbol:
        Symbol that was analysed.
    """
    base_regime: "TypesMarketRegime" = TypesMarketRegime.UNKNOWN
    regime: "TypesMarketRegime" = TypesMarketRegime.UNKNOWN
    trade_allowed: bool = True
    no_trade_reasons: List[str] = field(default_factory=list)
    volatility: VolatilityLevel = VolatilityLevel.NORMAL
    liquidity: LiquidityLevel = LiquidityLevel.NORMAL
    inputs: Dict[str, float] = field(default_factory=dict)
    symbol: str = ""


# ── MarketStateEngine ───────────────────────────────────────────────────────


class MarketStateEngine:
    """Market regime detection engine.

    Classifies market state based on price change, trend strength (ADX),
    RSI, volatility (ATR), and volume. Applies overrides for extreme
    conditions (PANIC → NO_TRADE, very low volume → NO_TRADE, etc.).
    """

    def __init__(self) -> None:
        self._regime_history: List[MarketStateResult] = []
        self._max_history = 100

    @property
    def regime_history(self) -> List[MarketStateResult]:
        return list(self._regime_history)

    @property
    def current_regime(self) -> TypesMarketRegime:
        if self._regime_history:
            return self._regime_history[-1].regime
        return TypesMarketRegime.UNKNOWN

    def get_regime(self) -> TypesMarketRegime:
        """Return the current regime (same as current_regime for API compatibility)."""
        return self.current_regime

    def get_market_state(self) -> MarketState:
        """Return a MarketState model summarizing current state."""
        if not self._regime_history:
            return MarketState()
        last = self._regime_history[-1]
        return MarketState(
            regime=last.regime,
            volatility=last.volatility,
            liquidity=last.liquidity,
        )

    def detect_regime(
        self,
        symbol: str = "",
        price_change_5d: float = 0.0,
        price_change_1d: float = 0.0,
        adx: float = 0.0,
        rsi: float = 50.0,
        atr_pct: float = 0.01,
        volume_ratio: float = 1.0,
        ema_trend: str = "neutral",
    ) -> MarketStateResult:
        """Detect market regime from technical inputs.

        Parameters
        ----------
        symbol:
            Symbol being analysed.
        price_change_5d:
            5-day price change in percent (e.g. -6.0 for -6%).
        price_change_1d:
            1-day price change in percent.
        adx:
            Average Directional Index.
        rsi:
            Relative Strength Index.
        atr_pct:
            Average True Range as % of price.
        volume_ratio:
            Recent volume / average volume.
        ema_trend:
            EMA trend direction: "bullish", "bearish", or "neutral".

        Returns
        -------
        MarketStateResult
            Detected regime with overrides.
        """
        inputs = {
            "price_change_5d": price_change_5d,
            "price_change_1d": price_change_1d,
            "adx": adx,
            "rsi": rsi,
            "atr_pct": atr_pct,
            "volume_ratio": volume_ratio,
            "ema_trend": ema_trend,
        }

        # ── Volatility classification ─────────────────────────────────
        if atr_pct > 2.5:
            volatility = VolatilityLevel.HIGH
        elif atr_pct < 0.5:
            volatility = VolatilityLevel.LOW
        else:
            volatility = VolatilityLevel.NORMAL

        # ── Liquidity classification ──────────────────────────────────
        if volume_ratio < 0.4:
            liquidity = LiquidityLevel.THIN
        elif volume_ratio > 1.8:
            liquidity = LiquidityLevel.DEEP
        else:
            liquidity = LiquidityLevel.NORMAL

        # ── Step 1: Detect base regime ────────────────────────────────
        base_regime = self._classify_base(
            price_change_5d, price_change_1d, adx, rsi, ema_trend, atr_pct, volume_ratio,
        )

        # ── Step 2: Apply overrides ──────────────────────────────────
        regime, trade_allowed, no_trade_reasons = self._apply_overrides(
            base_regime, price_change_5d, adx, rsi, atr_pct, volume_ratio,
            volatility, liquidity,
        )

        result = MarketStateResult(
            base_regime=base_regime,
            regime=regime,
            trade_allowed=trade_allowed,
            no_trade_reasons=no_trade_reasons,
            volatility=volatility,
            liquidity=liquidity,
            inputs=inputs,
            symbol=symbol,
        )

        self._regime_history.append(result)

        # Cap history
        if len(self._regime_history) > self._max_history:
            self._regime_history = self._regime_history[-self._max_history:]

        return result

    def _classify_base(
        self,
        price_change_5d: float,
        price_change_1d: float,
        adx: float,
        rsi: float,
        ema_trend: str,
        atr_pct: float,
        volume_ratio: float,
    ) -> TypesMarketRegime:

        # ── Panic / Risk-off (price drop overrides everything) ──
        if price_change_5d < -5.0:
            return TypesMarketRegime.PANIC
        if price_change_5d < -2.0:
            return TypesMarketRegime.RISK_OFF

        # ── Trending (ADX > 25) ─────────────────────────────────
        if adx > 25:
            if ema_trend == "bullish":
                return TypesMarketRegime.TRENDING_UP
            elif ema_trend == "bearish":
                return TypesMarketRegime.TRENDING_DOWN
            # Neutral EMA — use 1-day price change for direction
            if price_change_1d > 0.5:
                return TypesMarketRegime.TRENDING_UP
            elif price_change_1d < -0.5:
                return TypesMarketRegime.TRENDING_DOWN
            else:
                return TypesMarketRegime.TRENDING

        # ── Mean-revert (RSI extremes) ──────────────────────────
        if rsi > 75 or rsi < 25:
            return TypesMarketRegime.MEAN_REVERT

        # ── Volatility / ATR based regimes ──────────────────────
        if atr_pct > 2.5:
            return TypesMarketRegime.VOLATILE
        if atr_pct < 0.5 and volume_ratio < 0.5:
            return TypesMarketRegime.CALM

        # ── Default: RANGE ──────────────────────────────────────
        return TypesMarketRegime.RANGE

    def _apply_overrides(
        self,
        base_regime: TypesMarketRegime,
        price_change_5d: float,
        adx: float,
        rsi: float,
        atr_pct: float,
        volume_ratio: float,
        volatility: VolatilityLevel,
        liquidity: LiquidityLevel,
    ) -> Tuple[TypesMarketRegime, bool, List[str]]:
        """Apply overrides to the base regime.

        Returns (final_regime, trade_allowed, reasons_list).
        """

        regime = base_regime
        trade_allowed = True
        reasons: List[str] = []

        # PANIC → NO_TRADE
        if regime == TypesMarketRegime.PANIC:
            regime = TypesMarketRegime.NO_TRADE
            trade_allowed = False
            reasons.append("PANIC regime: price dropped more than 5% in 5 days")

        # RISK_OFF → also block
        if regime == TypesMarketRegime.RISK_OFF:
            trade_allowed = False
            reasons.append("RISK_OFF regime: price dropped 2-5% in 5 days")

        # Very low volume → NO_TRADE
        if volume_ratio < 0.2:
            regime = TypesMarketRegime.NO_TRADE
            trade_allowed = False
            reasons.append("Low volume — volume ratio below 0.2, insufficient liquidity")

        # High volatility + thin liquidity → NO_TRADE
        if volatility == VolatilityLevel.HIGH and liquidity == LiquidityLevel.THIN:
            regime = TypesMarketRegime.NO_TRADE
            trade_allowed = False
            reasons.append("High volatility with thin liquidity")

        return regime, trade_allowed, reasons
