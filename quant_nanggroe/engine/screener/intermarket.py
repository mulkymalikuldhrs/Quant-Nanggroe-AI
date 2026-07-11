"""Intermarket Engine — Intermarket correlation & rotation analysis.

Analyzes correlations between asset classes (stocks, bonds, commodities,
FX) and detects intermarket rotation signals.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult

logger = logging.getLogger(__name__)


class IntermarketEngine(ScreenerComponent):
    """Intermarket Correlation & Rotation Engine.

    Analyzes cross-asset relationships and rotation patterns
    to detect macro regime changes and intermarket divergences.
    """

    def __init__(self) -> None:
        super().__init__()

    @property
    def name(self) -> str:
        return "intermarket"

    @property
    def description(self) -> str:
        return "Intermarket correlation & rotation analysis"

    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        if not self._configured:
            return self._not_configured_result()

        # Analyze intermarket correlations
        correlation_score = self._analyze_correlations(data)

        # Analyze rotation signals
        rotation_score = self._analyze_rotation(data)

        # Combined
        combined = correlation_score * 0.5 + rotation_score * 0.5

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
                "correlation_score": correlation_score,
                "rotation_score": rotation_score,
                "regime": "risk_on" if combined > 0 else "risk_off",
            },
        )

    @staticmethod
    def _analyze_correlations(data: Dict[str, Any]) -> float:
        """Analyze intermarket correlations."""
        score = 0.0

        # Stock-bond correlation
        stock_bond_corr = data.get("stock_bond_correlation", -0.3)
        if stock_bond_corr > 0:
            score -= 0.2  # Positive stock-bond = risk-off signal
        else:
            score += 0.1  # Negative = normal regime

        # Dollar-commodity correlation
        dollar_commodity = data.get("dollar_commodity_correlation", -0.5)
        if dollar_commodity < -0.7:
            score += 0.15  # Strong inverse = commodity bullish

        return max(-1.0, min(1.0, score))

    @staticmethod
    def _analyze_rotation(data: Dict[str, Any]) -> float:
        """Analyze sector/asset rotation."""
        score = 0.0

        # Sector rotation
        sector_performance = data.get("sector_performance", {})
        if isinstance(sector_performance, dict):
            tech_vs_utilities = sector_performance.get("tech_vs_utilities", 0.0)
            if tech_vs_utilities > 0.05:
                score += 0.2  # Tech outperforming = risk-on
            elif tech_vs_utilities < -0.05:
                score -= 0.2  # Utilities outperforming = risk-off

        return max(-1.0, min(1.0, score))
