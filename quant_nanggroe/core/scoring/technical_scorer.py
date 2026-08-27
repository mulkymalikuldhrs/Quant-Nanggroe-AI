from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)


class TechnicalScorer(BaseScorer):
    weight: float = 0.10

    def __init__(self, ict_mode: str = "all"):
        self._ict_mode = ict_mode

    def _score_ict_quality(self, ctx: dict[str, Any], symbol: str) -> tuple[float, float]:
        ict_signal = ctx.get("ict_signal", {})
        if not ict_signal:
            return 0.0, 0.0

        direction = ict_signal.get("direction", 0)
        confidence_raw = ict_signal.get("confidence", 0.5)
        pattern = ict_signal.get("pattern", "")

        valid_patterns = ["fvg", "order_block", "displacement"]
        pattern_valid = 1.0 if pattern in valid_patterns else 0.0

        volume_conf = ict_signal.get("volume_ratio", 1.0)
        volume_quality = min(volume_conf / 2.0, 1.0)

        score = direction * confidence_raw * (0.6 * pattern_valid + 0.4 * volume_quality)
        confidence = confidence_raw * (0.5 + 0.5 * pattern_valid)

        return _clamp(score * 100, -100.0, 100.0), _clamp(confidence, 0.0, 1.0)

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        symbol = ctx.get("symbol", "")
        score, confidence = self._score_ict_quality(ctx, symbol)

        return ScorerResult(
            score=score,
            confidence=confidence,
            metadata={"ict_mode": self._ict_mode, "symbol": symbol},
        )
