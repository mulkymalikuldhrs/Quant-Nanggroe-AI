from __future__ import annotations

import logging
from typing import Any, Optional

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)


class BondScorer(BaseScorer):
    weight: float = 0.10

    def __init__(self, inversion_threshold: float = 0.0):
        self._inversion_threshold = inversion_threshold

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        t10_yield = ctx.get("t10_yield")
        t2_yield = ctx.get("t2_yield")
        t3m_yield = ctx.get("t3m_yield")

        if t10_yield is None or t2_yield is None:
            return ScorerResult(
                score=0.0,
                confidence=0.0,
                metadata={"source": "unavailable", "reason": "missing yield data"},
            )

        spread_2_10 = t10_yield - t2_yield
        inverted_2_10 = spread_2_10 < self._inversion_threshold

        score = 0.0
        confidence = 0.0
        signals = []

        if inverted_2_10:
            score = -40.0
            confidence = min(abs(spread_2_10) * 100, 0.8)
            signals.append("2s10s_inverted")
        else:
            steepness = min(spread_2_10 / 2.0, 1.0)
            score = steepness * 30.0
            confidence = min(steepness, 0.6)
            signals.append(f"steepness_{spread_2_10:.2f}")

        if t3m_yield is not None:
            spread_3m_10 = t10_yield - t3m_yield
            if spread_3m_10 < self._inversion_threshold and not inverted_2_10:
                score -= 20.0
                signals.append("3m10s_inverted")

        return ScorerResult(
            score=_clamp(score, -100.0, 100.0),
            confidence=float(_clamp(confidence, 0.0, 1.0)),
            metadata={
                "spread_2s10s": spread_2_10,
                "inverted": inverted_2_10,
                "signals": signals,
            },
        )
