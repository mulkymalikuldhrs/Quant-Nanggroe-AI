"""
Ensemble Voting Pipeline Step — plugs into AutonomousPipeline.

Adds a multi-source voting step between signal generation and council debate.
When enabled, the pipeline:
  1. Fetches signals from all registered adapters
  2. Combines with the primary strategy signal
  3. Uses SignalVotingSystem for weighted consensus
  4. Returns the voted signal with consensus metadata

This replaces the single-signal approach with a committee of signals.
"""
from __future__ import annotations

import logging
from typing import Any

from quant_nanggroe.engine.agentic.voting import (
    Bias,
    Signal,
    SignalVotingSystem,
    VoteResult,
)
from quant_nanggroe.engine.agentic.adapters import fetch_all_signals

logger = logging.getLogger(__name__)


class EnsembleVoter:
    """Runs the ensemble voting step within the autonomous pipeline.

    Usage in pipeline:
        voter = EnsembleVoter(config)
        voted_signal, vote_meta = voter.run(symbol, primary_signal, primary_confidence, dataframe=df)
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.voting_system = SignalVotingSystem(self.config.get("voting", {}))
        self.enabled = self.config.get("ensemble_voting_enabled", True)
        self.primary_weight = self.config.get("primary_weight", 1.5)

    def run(
        self,
        symbol: str,
        primary_bias: str,
        primary_confidence: float,
        dataframe=None,
    ) -> tuple[str, float, dict[str, Any]]:
        """Run ensemble voting.

        Args:
            symbol: Trading symbol
            primary_bias: Primary strategy signal ("buy"/"sell"/"neutral")
            primary_confidence: Primary strategy confidence (0-1)
            dataframe: Optional OHLCV data for adapters

        Returns:
            (final_bias_str, final_confidence, metadata_dict)
        """
        if not self.enabled:
            return primary_bias, primary_confidence, {"ensemble": "disabled"}

        # Build signal list starting with primary
        bias_map = {"buy": Bias.BUY, "sell": Bias.SELL, "neutral": Bias.NEUTRAL}
        primary_bias_enum = bias_map.get(primary_bias, Bias.NEUTRAL)

        signals = [
            Signal(
                bias=primary_bias_enum,
                confidence=primary_confidence,
                source="primary_strategy",
            )
        ]

        # Fetch external signals
        external = fetch_all_signals(symbol, dataframe=dataframe)
        signals.extend(external)

        # Run voting
        result: VoteResult = self.voting_system.vote(signals)

        # Convert back to string
        final_bias = result.final_bias.value
        final_conf = result.weighted_confidence

        metadata = {
            "ensemble": "active",
            "total_signals": len(signals),
            "final_bias": final_bias,
            "consensus_strength": round(result.consensus_strength, 4),
            "dissent_count": len(result.dissenters),
            "primary_was": primary_bias,
            "primary_confidence": primary_confidence,
            "votes": [
                {"source": v.source, "bias": v.bias.value, "confidence": v.confidence}
                for v in result.votes
            ],
        }

        if result.dissenters:
            metadata["dissenters"] = [
                {"source": d.source, "bias": d.bias.value, "confidence": d.confidence}
                for d in result.dissenters
            ]

        # If ensemble overrode primary, log it
        if final_bias != primary_bias and primary_bias != "neutral":
            logger.info(
                "Ensemble override: %s → %s (consensus=%.2f, %d signals)",
                primary_bias, final_bias, result.consensus_strength, len(signals),
            )

        return final_bias, final_conf, metadata
