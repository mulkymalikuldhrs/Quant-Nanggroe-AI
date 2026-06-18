"""Quant Scoring Engine — Quantitative setup scoring.

Objectively scores the quality of a trade setup by combining
analysis from all other screener engines into a single composite
score and grade.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult

logger = logging.getLogger(__name__)


class QuantScoringEngine(ScreenerComponent):
    """Quant Scoring Engine.

    Objectively scores trade setup quality by combining:
    - Macro alignment score
    - Fundamental alignment score
    - Positioning asymmetry score
    - SMT confirmation score
    - Structure quality score
    - Liquidity clarity score
    - Execution risk score
    - Risk/reward quality score
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "quant_scoring"

    @property
    def description(self) -> str:
        return "Quantitative setup scoring (composite grade)"

    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        if not self._configured:
            return self._not_configured_result()

        # Score each dimension
        scores = {
            "macro_alignment": self._score_macro(data),
            "fundamental_alignment": self._score_fundamental(data),
            "positioning_asymmetry": self._score_positioning(data),
            "smt_confirmation": self._score_smt(data),
            "structure_quality": self._score_structure(data),
            "liquidity_clarity": self._score_liquidity(data),
            "execution_risk": self._score_execution_risk(data),
            "rr_quality": self._score_rr(data),
        }

        # Weights for each dimension
        weights = {
            "macro_alignment": 0.15,
            "fundamental_alignment": 0.15,
            "positioning_asymmetry": 0.12,
            "smt_confirmation": 0.13,
            "structure_quality": 0.15,
            "liquidity_clarity": 0.10,
            "execution_risk": 0.10,
            "rr_quality": 0.10,
        }

        # Weighted composite
        total_score = sum(scores[k] * weights[k] for k in scores)

        # Grade
        grade = self._assign_grade(total_score)

        direction = (
            ScreenerDirection.BULLISH
            if total_score > 0.3
            else ScreenerDirection.BEARISH
            if total_score < -0.3
            else ScreenerDirection.NEUTRAL
        )

        return ScreenerResult(
            component_name=self.name,
            direction=direction,
            score=total_score,
            confidence=min(0.9, abs(total_score) + 0.3),
            details={
                "scores": scores,
                "total_score": total_score,
                "trade_grade": grade,
            },
        )

    @staticmethod
    def _score_macro(data: Dict[str, Any]) -> float:
        return data.get("macro_score", 0.0)

    @staticmethod
    def _score_fundamental(data: Dict[str, Any]) -> float:
        return data.get("fundamental_score", 0.0)

    @staticmethod
    def _score_positioning(data: Dict[str, Any]) -> float:
        return data.get("positioning_score", 0.0)

    @staticmethod
    def _score_smt(data: Dict[str, Any]) -> float:
        return data.get("smt_score", 0.0)

    @staticmethod
    def _score_structure(data: Dict[str, Any]) -> float:
        return data.get("structure_score", 0.0)

    @staticmethod
    def _score_liquidity(data: Dict[str, Any]) -> float:
        return data.get("liquidity_score", 0.0)

    @staticmethod
    def _score_execution_risk(data: Dict[str, Any]) -> float:
        return data.get("execution_risk_score", 0.0)

    @staticmethod
    def _score_rr(data: Dict[str, Any]) -> float:
        rr = data.get("risk_reward_ratio", 1.0)
        if rr > 3.0:
            return 0.8
        elif rr > 2.0:
            return 0.5
        elif rr > 1.5:
            return 0.2
        else:
            return -0.3

    @staticmethod
    def _assign_grade(score: float) -> str:
        if score > 0.6:
            return "A+"
        elif score > 0.4:
            return "A"
        elif score > 0.2:
            return "B+"
        elif score > 0.0:
            return "B"
        elif score > -0.2:
            return "C"
        elif score > -0.4:
            return "D"
        else:
            return "F"
