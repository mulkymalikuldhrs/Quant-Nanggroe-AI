from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

from quant_nanggroe.core.scoring.base import BaseScorer, ScorerResult, _clamp

logger = logging.getLogger(__name__)

EXECUTION_CONFIDENCE_THRESHOLD = 0.60
TRADE_THRESHOLD = 20.0


@dataclass
class ScoredSignal:
    # DEPRECATED — use quant_nanggroe.types.signals.Signal instead.
    # composite_score, bias -> signal_type, details, override_aggregator all in canonical.
    composite_score: float
    confidence: float
    bias: str
    details: list[tuple[str, ScorerResult]] = field(default_factory=list)
    override_aggregator: bool = False


class FusionEngine:
    def __init__(self, scorers: Optional[list[BaseScorer]] = None):
        self._scorers: list[BaseScorer] = scorers or []

    def add_scorer(self, scorer: BaseScorer) -> None:
        self._scorers.append(scorer)

    def evaluate(self, ctx: dict[str, Any]) -> ScoredSignal:
        if not self._scorers:
            return ScoredSignal(
                composite_score=0.0,
                confidence=0.0,
                bias="neutral",
                override_aggregator=False,
            )

        total_weight = sum(s.weight for s in self._scorers)
        if total_weight <= 0:
            return ScoredSignal(
                composite_score=0.0,
                confidence=0.0,
                bias="neutral",
                override_aggregator=False,
            )

        if abs(total_weight - 1.0) > 0.001:
            for s in self._scorers:
                s.weight /= total_weight
            total_weight = 1.0

        assert abs(sum(s.weight for s in self._scorers) - 1.0) < 0.001, \
            f"FusionEngine scorer weights must sum to 1.0, got {sum(s.weight for s in self._scorers)}"

        details: list[tuple[str, ScorerResult]] = []
        weighted_sum = 0.0
        weighted_conf_sum = 0.0

        for scorer in self._scorers:
            try:
                result: ScorerResult = scorer.score(ctx)
                details.append((scorer.__class__.__name__, result))
                weighted_sum += result.score * scorer.weight
                weighted_conf_sum += result.confidence * scorer.weight
            except Exception as exc:
                logger.debug("%s failed: %s", scorer.__class__.__name__, exc)
                details.append((scorer.__class__.__name__, ScorerResult(score=0.0, confidence=0.0)))

        composite_score = weighted_sum
        avg_confidence = weighted_conf_sum

        composite_score = _clamp(composite_score, -100.0, 100.0)
        confidence = float(math.tanh(abs(composite_score) / 40.0))

        confidence = min(confidence, avg_confidence + 0.2)

        if composite_score > TRADE_THRESHOLD:
            bias = "buy"
        elif composite_score < -TRADE_THRESHOLD:
            bias = "sell"
        else:
            bias = "neutral"

        override = confidence >= EXECUTION_CONFIDENCE_THRESHOLD and bias != "neutral"

        return ScoredSignal(
            composite_score=composite_score,
            confidence=confidence,
            bias=bias,
            details=details,
            override_aggregator=override,
        )
