"""Sentiment Analysis — based on RavenPack Sentiment Inflection Points.

Cross-over strategy between short-term and long-term news sentiment.
Key finding: Information Ratio of 1.61 for 10-hour holding period.

Reference: Intraday Forex Trading Based on Sentiment Inflection Points
RavenPack Research (2013) — SSRN 2198816
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SentimentSignal:
    # DEPRECATED — use quant_nanggroe.types.signals.Signal instead.
    # buy/sell bools -> signal_type + indicators, short_ma/long_ma/difference/strength -> evidence/factors.
    # This is a sentiment crossover signal — migration recommended.
    buy: bool
    sell: bool
    short_ma: float
    long_ma: float
    difference: float
    strength: float
    holding_period: str


class SentimentAnalyzer:
    """Analyze news sentiment using moving average crossover.

    Uses short-term (1-week) vs long-term (3-month) sentiment MAs
    to detect inflection points that predict intraday price moves.
    """

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 63,
    ):
        self.short_window = short_window
        self.long_window = long_window

    def compute_scores(self, news_items: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute sentiment scores from news items."""
        if not news_items:
            return {"short_ma": 0.0, "long_ma": 0.0, "score": 0.0}
        recent = news_items[:self.short_window]
        extended = news_items[:self.long_window]
        short_ma = sum(
            item.get("sentiment", 0) for item in recent
        ) / len(recent) if recent else 0.0
        long_ma = sum(
            item.get("sentiment", 0) for item in extended
        ) / len(extended) if extended else 0.0
        return {
            "short_ma": round(short_ma, 4),
            "long_ma": round(long_ma, 4),
            "score": round(short_ma - long_ma, 4),
        }

    def detect_crossover(self, scores: Dict[str, float]) -> SentimentSignal:
        """Detect sentiment inflection point (crossover)."""
        short_ma = scores.get("short_ma", 0)
        long_ma = scores.get("long_ma", 0)
        diff = short_ma - long_ma

        strength = min(abs(diff) / 0.1, 1.0)
        buy = short_ma > long_ma and diff > 0.02
        sell = short_ma < long_ma and diff < -0.02

        return SentimentSignal(
            buy=buy,
            sell=sell,
            short_ma=short_ma,
            long_ma=long_ma,
            difference=diff,
            strength=strength,
            holding_period="10h" if strength > 0.7 else "3h",
        )

    def analyze(self, news_items: List[Dict[str, Any]]) -> Optional[SentimentSignal]:
        if not news_items:
            return None
        scores = self.compute_scores(news_items)
        return self.detect_crossover(scores)
