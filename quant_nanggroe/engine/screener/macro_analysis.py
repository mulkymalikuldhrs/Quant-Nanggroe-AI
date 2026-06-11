"""Macro Analysis Engine — Macro regime & policy analysis.

Analyzes macro regimes, central bank policy, economic cycles,
and geopolitical factors to assess macro-level pressure.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult

logger = logging.getLogger(__name__)


class MacroAnalysisEngine(ScreenerComponent):
    """Macro Analysis Engine.

    Analyzes macro regimes (expansion/contraction), policy stance,
    economic cycle position, and geopolitical factors.
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "macro_analysis"

    @property
    def description(self) -> str:
        return "Macro regime & policy analysis (economic cycles, geopolitical)"

    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        if not self._configured:
            return self._not_configured_result()

        regime_score = self._analyze_regime(data)
        policy_score = self._analyze_policy(data)
        cycle_score = self._analyze_cycle(data)
        geopolitical_score = self._analyze_geopolitical(data)

        combined = (
            regime_score * 0.30
            + policy_score * 0.30
            + cycle_score * 0.25
            + geopolitical_score * 0.15
        )

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
                "regime_score": regime_score,
                "policy_score": policy_score,
                "cycle_score": cycle_score,
                "geopolitical_score": geopolitical_score,
                "regime_type": "expansion" if combined > 0 else "contraction",
            },
        )

    @staticmethod
    def _analyze_regime(data: Dict[str, Any]) -> float:
        score = 0.0
        gdp_growth = data.get("gdp_growth", 2.0)
        if gdp_growth > 3.0:
            score += 0.4
        elif gdp_growth < 1.0:
            score -= 0.4
        return max(-1.0, min(1.0, score))

    @staticmethod
    def _analyze_policy(data: Dict[str, Any]) -> float:
        score = 0.0
        policy_stance = data.get("policy_stance", "neutral")
        if policy_stance == "accommodative":
            score += 0.4
        elif policy_stance == "restrictive":
            score -= 0.4
        return max(-1.0, min(1.0, score))

    @staticmethod
    def _analyze_cycle(data: Dict[str, Any]) -> float:
        score = 0.0
        cycle_phase = data.get("economic_cycle", "mid")
        if cycle_phase == "early":
            score += 0.3
        elif cycle_phase == "late":
            score -= 0.3
        return max(-1.0, min(1.0, score))

    @staticmethod
    def _analyze_geopolitical(data: Dict[str, Any]) -> float:
        score = 0.0
        risk_level = data.get("geopolitical_risk", "moderate")
        if risk_level == "low":
            score += 0.2
        elif risk_level == "high":
            score -= 0.3
        return max(-1.0, min(1.0, score))
