from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from quant_nanggroe.core.scoring.base import BaseScorer
from quant_nanggroe.core.scoring.bond_scorer import BondScorer
from quant_nanggroe.core.scoring.economic_scorer import EconomicScorer
from quant_nanggroe.core.scoring.geo_scorer import GeopoliticalScorer
from quant_nanggroe.core.scoring.macro_scorer import MacroScorer
from quant_nanggroe.core.scoring.sentiment_scorer import SentimentScorer
from quant_nanggroe.core.scoring.technical_scorer import TechnicalScorer
from quant_nanggroe.core.scoring.volatility_scorer import VolatilityScorer
from quant_nanggroe.core.scoring.crypto_scorer import CryptoScorer
from quant_nanggroe.core.news import NewsScorer
from quant_nanggroe.core.scoring.fusion_engine import FusionEngine, ScoredSignal

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    scored_signal: ScoredSignal
    status: str
    execution_decision: str = "skip"


class QuantPipeline:
    def __init__(self, scorers: Optional[list[BaseScorer]] = None):
        default_scorers = [
            MacroScorer(),
            EconomicScorer(),
            BondScorer(),
            CryptoScorer(),
            NewsScorer(),
            SentimentScorer(),
            TechnicalScorer(),
            VolatilityScorer(),
            GeopoliticalScorer(),
        ]
        self._fusion = FusionEngine(scorers or default_scorers)

    def analyze(self, ctx: dict[str, Any]) -> PipelineResult:
        scored = self._fusion.evaluate(ctx)
        if scored.override_aggregator:
            return PipelineResult(
                scored_signal=scored,
                status="actionable",
                execution_decision="execute" if scored.bias != "neutral" else "skip",
            )
        return PipelineResult(
            scored_signal=scored,
            status="insufficient_confidence",
            execution_decision="fallback",
        )
