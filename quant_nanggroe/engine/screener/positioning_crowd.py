"""Positioning & Crowd Engine — Positioning & crowd sentiment analysis.

Analyzes market positioning data, crowd sentiment, commitment of
traders, and contrarian signals from extreme positioning.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult

logger = logging.getLogger(__name__)


class PositioningCrowdEngine(ScreenerComponent):
    """Positioning & Crowd Sentiment Engine.

    Analyzes:
    - Commitment of Traders (COT) positioning
    - Retail vs institutional sentiment
    - Contrarian signals from extreme positioning
    - Social sentiment metrics
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "positioning_crowd"

    @property
    def description(self) -> str:
        return "Positioning & crowd sentiment (COT, contrarian, social)"

    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        if not self._configured:
            return self._not_configured_result()

        cot_score = self._analyze_cot(data)
        sentiment_score = self._analyze_sentiment(data)
        contrarian_score = self._analyze_contrarian(data)

        combined = cot_score * 0.35 + sentiment_score * 0.35 + contrarian_score * 0.30

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
            confidence=min(0.8, abs(combined) + 0.3),
            details={
                "cot_score": cot_score,
                "sentiment_score": sentiment_score,
                "contrarian_score": contrarian_score,
                "crowd_positioning": "crowded_long" if sentiment_score < -0.3 else "crowded_short" if sentiment_score > 0.3 else "balanced",
            },
        )

    @staticmethod
    def _analyze_cot(data: Dict[str, Any]) -> float:
        """Analyze COT positioning."""
        cot = data.get("cot_data", {})
        if not isinstance(cot, dict):
            return 0.0

        # Net positioning (commercial vs speculative)
        commercial_net = cot.get("commercial_net", 0.0)
        speculative_net = cot.get("speculative_net", 0.0)

        # Contrarian: extreme speculative positioning is often wrong
        if abs(speculative_net) > 0.7:
            return -0.3 * np.sign(speculative_net)

        # Commercial positioning is typically "smart money"
        return max(-0.3, min(0.3, commercial_net * 0.3))

    @staticmethod
    def _analyze_sentiment(data: Dict[str, Any]) -> float:
        """Analyze crowd sentiment."""
        sentiment = data.get("sentiment", {})
        if not isinstance(sentiment, dict):
            return 0.0

        # Bull/bear ratio
        bull_bear_ratio = sentiment.get("bull_bear_ratio", 1.0)
        if bull_bear_ratio > 2.0:
            return -0.3  # Too bullish = contrarian bearish
        elif bull_bear_ratio < 0.5:
            return 0.3  # Too bearish = contrarian bullish

        return 0.0

    @staticmethod
    def _analyze_contrarian(data: Dict[str, Any]) -> float:
        """Analyze contrarian signals."""
        extreme = data.get("extreme_positioning", False)
        if extreme:
            direction = data.get("extreme_direction", "long")
            if direction == "long":
                return -0.4  # Contrarian: fade extreme longs
            else:
                return 0.4  # Contrarian: fade extreme shorts

        return 0.0
