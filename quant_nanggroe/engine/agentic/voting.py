"""
Multi-Signal Voting System — ported from E:\\trading\\hedge_fund.py
Enhanced for QNA integration with proper async support.

Each signal provider returns:
  {"bias": "buy"|"sell"|"neutral", "confidence": 0-1, "source": "name"}

Voting aggregates all signals with weighted confidence.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Bias(str, Enum):
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"


@dataclass
class Signal:
    bias: Bias
    confidence: float  # 0.0 - 1.0
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class VoteResult:
    final_bias: Bias
    weighted_confidence: float
    votes: list[Signal]
    consensus_strength: float  # how much agreement (0-1)
    dissenters: list[Signal]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_bias": self.final_bias.value,
            "weighted_confidence": round(self.weighted_confidence, 4),
            "consensus_strength": round(self.consensus_strength, 4),
            "vote_count": len(self.votes),
            "dissent_count": len(self.dissenters),
            "votes": [
                {"bias": v.bias.value, "confidence": v.confidence, "source": v.source}
                for v in self.votes
            ],
            "timestamp": self.timestamp,
        }


class SignalVotingSystem:
    """Aggregates multiple signal providers with weighted voting.

    Features:
    - Per-source weight configuration
    - Minimum consensus threshold
    - Confidence-weighted averaging
    - Dissenter tracking
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.source_weights: dict[str, float] = self.config.get("source_weights", {})
        self.min_confidence_threshold = self.config.get("min_confidence", 0.3)
        self.min_consensus = self.config.get("min_consensus", 0.5)
        self.default_weight = self.config.get("default_weight", 1.0)

    def get_weight(self, source: str) -> float:
        return self.source_weights.get(source, self.default_weight)

    def vote(self, signals: list[Signal]) -> VoteResult:
        """Aggregate signals into a single decision.

        Algorithm:
        1. Filter out low-confidence signals
        2. Weight each signal by source weight * confidence
        3. Sum weighted votes per bias
        4. Select bias with highest total weight
        5. Calculate consensus strength
        """
        # Filter low-confidence
        valid = [s for s in signals if s.confidence >= self.min_confidence_threshold]

        if not valid:
            return VoteResult(
                final_bias=Bias.NEUTRAL,
                weighted_confidence=0.0,
                votes=[],
                consensus_strength=0.0,
                dissenters=[],
            )

        # Weighted sums per bias
        bias_weights: dict[Bias, float] = {b: 0.0 for b in Bias}
        total_weight = 0.0

        for sig in valid:
            w = self.get_weight(sig.source) * sig.confidence
            bias_weights[sig.bias] += w
            total_weight += w

        if total_weight == 0:
            return VoteResult(
                final_bias=Bias.NEUTRAL,
                weighted_confidence=0.0,
                votes=valid,
                consensus_strength=0.0,
                dissenters=[],
            )

        # Pick winner
        final_bias = max(bias_weights, key=lambda b: bias_weights[b])
        winning_weight = bias_weights[final_bias]
        weighted_confidence = winning_weight / total_weight

        # Consensus = how much of total weight agrees
        consensus_strength = winning_weight / total_weight

        # Dissenters = signals that voted differently
        dissenters = [s for s in valid if s.bias != final_bias]

        # If consensus too low, force neutral
        if consensus_strength < self.min_consensus and final_bias != Bias.NEUTRAL:
            logger.info(
                "Low consensus (%.2f < %.2f), forcing NEUTRAL",
                consensus_strength,
                self.min_consensus,
            )
            final_bias = Bias.NEUTRAL
            weighted_confidence *= 0.5  # penalize

        return VoteResult(
            final_bias=final_bias,
            weighted_confidence=weighted_confidence,
            votes=valid,
            consensus_strength=consensus_strength,
            dissenters=dissenters,
        )
