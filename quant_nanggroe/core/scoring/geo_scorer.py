from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)


class GeopoliticalScorer(BaseScorer):
    weight: float = 0.05

    def score(self, ctx: dict[str, Any]) -> ScorerResult:
        gpr_index = ctx.get("gpr_index")
        risk_delta = ctx.get("geopolitical_risk_delta")
        active_conflicts = ctx.get("active_conflicts", [])

        score = 0.0
        confidence = 0.0
        signals = []

        if gpr_index is not None:
            gpr_dev = (gpr_index - 100.0) / 100.0
            score += _clamp(gpr_dev * -50, -50.0, 0.0)
            confidence += 0.4
            signals.append(f"gpr_{gpr_index:.0f}")

        if risk_delta is not None:
            score += _clamp(-risk_delta / 2.0, -50.0, 0.0)
            confidence += 0.3
            signals.append(f"risk_delta_{risk_delta:.1f}")

        if active_conflicts:
            severity = len(active_conflicts)
            score -= _clamp(severity * 10.0, -30.0, 0.0)
            confidence += 0.3
            signals.append(f"conflicts_{severity}")

        return ScorerResult(
            score=_clamp(score, -100.0, 100.0),
            confidence=float(_clamp(confidence, 0.0, 1.0)),
            metadata={"signals": signals},
        )
