from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)


class VolatilityScorer(BaseScorer):
    weight: float = 0.05

    VIX_BASELINE = 18.0
    VIX_EXTREME_HIGH = 35.0
    VIX_EXTREME_LOW = 12.0

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        vix = ctx.get("vix")
        if vix is None:
            return ScorerResult(score=0.0, confidence=0.0, metadata={"source": "unavailable"})

        vix_dev = (vix - self.VIX_BASELINE) / self.VIX_BASELINE
        score = _clamp(vix_dev * -100, -100.0, 100.0)
        confidence = _clamp(abs(vix_dev), 0.0, 1.0)

        regime = "normal"
        if vix >= self.VIX_EXTREME_HIGH:
            regime = "extreme_fear"
        elif vix <= self.VIX_EXTREME_LOW:
            regime = "complacent"
        elif vix > 25:
            regime = "elevated"

        return ScorerResult(
            score=score,
            confidence=confidence,
            metadata={"vix": vix, "regime": regime, "deviation": round(vix_dev, 3)},
        )
