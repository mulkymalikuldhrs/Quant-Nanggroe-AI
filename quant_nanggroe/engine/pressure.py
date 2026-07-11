"""Market buy/sell pressure engine for the AI-MultiColony finance module.

Analyses order flow, volume patterns, and price action to determine
the prevailing buy/sell pressure in the market.  This intelligence
is used to inform trade timing and direction decisions.

Pressure analysis considers:
* Volume-weighted price movement
* Order flow imbalance
* Tick-by-tick price action
* Support/resistance proximity
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class PressureDirection(str, Enum):
    """Direction of market pressure."""
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class PressureStrength(str, Enum):
    """Strength of market pressure."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    EXTREME = "extreme"


# ── Models ───────────────────────────────────────────────────────────────────


class PressureResult(BaseModel):
    """Result from a pressure analysis."""
    model_config = ConfigDict(frozen=False)

    result_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    symbol: str = ""
    direction: PressureDirection = PressureDirection.NEUTRAL
    strength: PressureStrength = PressureStrength.WEAK
    buy_pressure: float = 0.0  # 0-1
    sell_pressure: float = 0.0  # 0-1
    net_pressure: float = 0.0  # -1 to +1 (negative = sell, positive = buy)
    volume_imbalance: float = 0.0  # -1 to +1
    price_momentum: float = 0.0  # Rate of change
    confidence: float = 0.0
    indicators: Dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OHLCVBar(BaseModel):
    """A single OHLCV bar."""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0
    timestamp: Optional[datetime] = None


class PressureConfig(BaseModel):
    """Configuration for pressure analysis."""
    model_config = ConfigDict(frozen=False)

    lookback_period: int = 20
    volume_weight_factor: float = 0.5
    momentum_weight_factor: float = 0.3
    imbalance_weight_factor: float = 0.2
    strong_threshold: float = 0.6
    extreme_threshold: float = 0.8
    smoothing_period: int = 5


# ── Pressure Engine ──────────────────────────────────────────────────────────


class PressureEngine:
    """Analyses market buy/sell pressure.

    Uses volume analysis, price momentum, and order flow
    approximation to determine market pressure.

    Usage::

        engine = PressureEngine()
        bars = [OHLCVBar(open=100, high=102, low=99, close=101, volume=1000), ...]
        result = engine.analyze(bars, symbol="AAPL")
    """

    def __init__(self, config: Optional[PressureConfig] = None):
        self._config = config or PressureConfig()
        self._results: List[PressureResult] = []

    def analyze(
        self,
        bars: List[OHLCVBar],
        symbol: str = "",
    ) -> PressureResult:
        """Analyse buy/sell pressure from OHLCV data.

        Parameters
        ----------
        bars:
            List of OHLCV bars (most recent last).
        symbol:
            Symbol being analyzed.

        Returns
        -------
        PressureResult
            Pressure analysis result.
        """
        if len(bars) < 3:
            return PressureResult(
                symbol=symbol,
                direction=PressureDirection.NEUTRAL,
                confidence=0.0,
            )

        # Calculate indicators
        volume_imbalance = self._compute_volume_imbalance(bars)
        price_momentum = self._compute_price_momentum(bars)
        vwap_deviation = self._compute_vwap_deviation(bars)
        close_position = self._compute_close_position(bars)

        # Weighted pressure calculation
        cfg = self._config
        buy_signals = 0.0
        sell_signals = 0.0

        # Volume imbalance contribution
        if volume_imbalance > 0:
            buy_signals += volume_imbalance * cfg.volume_weight_factor
        else:
            sell_signals += abs(volume_imbalance) * cfg.volume_weight_factor

        # Price momentum contribution
        if price_momentum > 0:
            buy_signals += min(1.0, abs(price_momentum)) * cfg.momentum_weight_factor
        else:
            sell_signals += min(1.0, abs(price_momentum)) * cfg.momentum_weight_factor

        # Close position contribution
        if close_position > 0.5:
            buy_signals += (close_position - 0.5) * 2 * cfg.imbalance_weight_factor
        else:
            sell_signals += (0.5 - close_position) * 2 * cfg.imbalance_weight_factor

        # Normalize
        total = buy_signals + sell_signals
        buy_pressure = buy_signals / total if total > 0 else 0.5
        sell_pressure = sell_signals / total if total > 0 else 0.5
        net_pressure = buy_pressure - sell_pressure

        # Determine direction
        if abs(net_pressure) < 0.1:
            direction = PressureDirection.NEUTRAL
        elif buy_pressure > 0.7 and sell_pressure < 0.3:
            direction = PressureDirection.BUY
        elif sell_pressure > 0.7 and buy_pressure < 0.3:
            direction = PressureDirection.SELL
        else:
            direction = PressureDirection.MIXED

        # Determine strength
        max_pressure = max(buy_pressure, sell_pressure)
        if max_pressure >= cfg.extreme_threshold:
            strength = PressureStrength.EXTREME
        elif max_pressure >= cfg.strong_threshold:
            strength = PressureStrength.STRONG
        elif max_pressure >= 0.4:
            strength = PressureStrength.MODERATE
        else:
            strength = PressureStrength.WEAK

        # Confidence
        confidence = min(1.0, max(0.0, abs(net_pressure) * 2))

        result = PressureResult(
            symbol=symbol,
            direction=direction,
            strength=strength,
            buy_pressure=round(buy_pressure, 3),
            sell_pressure=round(sell_pressure, 3),
            net_pressure=round(net_pressure, 3),
            volume_imbalance=round(volume_imbalance, 3),
            price_momentum=round(price_momentum, 4),
            confidence=round(confidence, 3),
            indicators={
                "vwap_deviation": round(vwap_deviation, 4),
                "close_position": round(close_position, 3),
            },
        )

        self._results.append(result)
        return result

    def analyze_from_arrays(
        self,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        symbol: str = "",
    ) -> PressureResult:
        """Analyze pressure from separate price/volume arrays."""
        n = min(len(opens), len(highs), len(lows), len(closes), len(volumes))
        bars = [
            OHLCVBar(open=opens[i], high=highs[i], low=lows[i],
                     close=closes[i], volume=volumes[i])
            for i in range(n)
        ]
        return self.analyze(bars, symbol)

    # ── Indicator computations ──────────────────────────────────────────

    @staticmethod
    def _compute_volume_imbalance(bars: List[OHLCVBar]) -> float:
        """Compute volume imbalance (up volume vs down volume).

        Returns
        -------
        float
            -1 to +1 (positive = more up volume).
        """
        up_volume = 0.0
        down_volume = 0.0

        for bar in bars:
            if bar.close >= bar.open:
                up_volume += bar.volume
            else:
                down_volume += bar.volume

        total = up_volume + down_volume
        if total == 0:
            return 0.0
        return (up_volume - down_volume) / total

    @staticmethod
    def _compute_price_momentum(bars: List[OHLCVBar]) -> float:
        """Compute price momentum as rate of change."""
        if len(bars) < 2:
            return 0.0

        # Use exponential weighting for recent bars
        n = len(bars)
        weights = [math.exp(i / n) for i in range(n)]
        weighted_sum = sum(w * b.close for w, b in zip(weights, bars))
        total_weight = sum(weights)

        if total_weight == 0 or bars[0].close == 0:
            return 0.0

        weighted_avg = weighted_sum / total_weight
        return (weighted_avg - bars[0].close) / bars[0].close

    @staticmethod
    def _compute_vwap_deviation(bars: List[OHLCVBar]) -> float:
        """Compute deviation of current price from VWAP."""
        if not bars:
            return 0.0

        total_volume = sum(b.volume for b in bars)
        if total_volume == 0:
            return 0.0

        vwap = sum(
            ((b.high + b.low + b.close) / 3) * b.volume
            for b in bars
        ) / total_volume

        current_price = bars[-1].close
        if vwap == 0:
            return 0.0

        return (current_price - vwap) / vwap

    @staticmethod
    def _compute_close_position(bars: List[OHLCVBar]) -> float:
        """Compute where the close sits relative to the bar's range.

        Returns
        -------
        float
            0.0 = close at low, 1.0 = close at high, 0.5 = mid-range.
        """
        if not bars:
            return 0.5

        # Average across recent bars
        positions = []
        for bar in bars[-10:]:
            range_val = bar.high - bar.low
            if range_val > 0:
                positions.append((bar.close - bar.low) / range_val)
            else:
                positions.append(0.5)

        return sum(positions) / len(positions)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def history(self) -> List[PressureResult]:
        return list(self._results)

    @property
    def config(self) -> PressureConfig:
        return self._config

    @property
    def stats(self) -> Dict[str, Any]:
        """Pressure engine statistics."""
        direction_counts: Dict[str, int] = {}
        for result in self._results:
            key = result.direction.value
            direction_counts[key] = direction_counts.get(key, 0) + 1

        return {
            "total_analyses": len(self._results),
            "direction_distribution": direction_counts,
        }


# ── Backward-compatible aliases ──────────────────────────────────────
PressureNormalizationEngine = PressureEngine
from dataclasses import dataclass


@dataclass
class PressureInput:
    """Input dataclass for pressure engine analysis."""
    trend_direction: str = "neutral"
    trend_strength: float = 0.0
