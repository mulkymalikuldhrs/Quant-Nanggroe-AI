"""Market Structure Engine — Market structure & regime detection.

Detects market structure (trending/ranging), volatility regimes,
and key structure levels (swing points, channels).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult

logger = logging.getLogger(__name__)


class MarketStructureEngine(ScreenerComponent):
    """Market Structure Engine.

    Detects market structure (trending/ranging/volatile), identifies
    swing points, channels, and structural breaks.
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "market_structure"

    @property
    def description(self) -> str:
        return "Market structure & regime detection (trend, range, structure breaks)"

    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        if not self._configured:
            return self._not_configured_result()

        prices = data.get("prices")
        if prices is None or not isinstance(prices, pd.DataFrame):
            # Use basic analysis if no price data
            return ScreenerResult(
                component_name=self.name,
                direction=ScreenerDirection.NEUTRAL,
                score=0.0,
                confidence=0.3,
                details={"regime": "unknown"},
                message="No price data provided for structure analysis",
            )

        trend_score = self._analyze_trend(prices)
        volatility_score = self._analyze_volatility_regime(prices)
        structure_score = self._analyze_structure(prices)

        combined = trend_score * 0.4 + volatility_score * 0.2 + structure_score * 0.4

        direction = (
            ScreenerDirection.BULLISH
            if combined > 0.2
            else ScreenerDirection.BEARISH
            if combined < -0.2
            else ScreenerDirection.NEUTRAL
        )

        return ScreenerResult(
            component_name=self.name,
            direction=direction,
            score=combined,
            confidence=min(0.85, abs(combined) + 0.3),
            details={
                "trend_score": trend_score,
                "volatility_regime": "high" if volatility_score > 0.5 else "normal",
                "structure_score": structure_score,
                "regime": self._classify_regime(trend_score, volatility_score),
            },
        )

    @staticmethod
    def _analyze_trend(prices: pd.DataFrame) -> float:
        if "close" not in prices.columns or len(prices) < 20:
            return 0.0

        close = prices["close"]
        sma_10 = close.rolling(10, min_periods=10).mean()
        sma_50 = close.rolling(50, min_periods=min(50, len(close))).mean()

        current = float(close.iloc[-1])
        sma10_val = float(sma_10.iloc[-1]) if not sma_10.iloc[-1] != sma_10.iloc[-1] else current

        score = 0.0
        if current > sma10_val:
            score += 0.3
        else:
            score -= 0.3

        # Higher highs / lower lows
        if len(close) >= 10:
            recent_high = float(close.iloc[-5:].max())
            prev_high = float(close.iloc[-10:-5].max()) if len(close) >= 10 else recent_high
            if recent_high > prev_high:
                score += 0.3
            else:
                score -= 0.3

        return max(-1.0, min(1.0, score))

    @staticmethod
    def _analyze_volatility_regime(prices: pd.DataFrame) -> float:
        if "close" not in prices.columns or len(prices) < 20:
            return 0.5

        returns = prices["close"].pct_change().dropna()
        if len(returns) < 10:
            return 0.5

        vol = float(returns.rolling(20, min_periods=5).std().iloc[-1])
        annual_vol = vol * np.sqrt(252)
        return min(1.0, annual_vol / 0.4)

    @staticmethod
    def _analyze_structure(prices: pd.DataFrame) -> float:
        if "close" not in prices.columns or len(prices) < 30:
            return 0.0

        close = prices["close"]
        # Check for structure break (close above/below recent range)
        range_high = float(close.iloc[-30:-5].max())
        range_low = float(close.iloc[-30:-5].min())
        current = float(close.iloc[-1])

        if current > range_high:
            return 0.5  # Bullish breakout
        elif current < range_low:
            return -0.5  # Bearish breakout
        return 0.0

    @staticmethod
    def _classify_regime(trend: float, volatility: float) -> str:
        if abs(trend) > 0.3 and volatility < 0.6:
            return "trending"
        elif abs(trend) < 0.2 and volatility < 0.4:
            return "ranging"
        elif volatility > 0.7:
            return "volatile"
        else:
            return "transitional"
