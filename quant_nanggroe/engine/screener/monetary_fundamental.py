"""Monetary & Fundamental Engine — Analyzes monetary and fundamental drivers.

Analyzes interest rates, inflation, central bank policy, earnings,
valuation metrics, and sector rotation to determine fundamental
pressure on asset classes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from quant_nanggroe.engine.screener.base import ScreenerComponent, ScreenerDirection, ScreenerResult

logger = logging.getLogger(__name__)


class MonetaryFundamentalEngine(ScreenerComponent):
    """Monetary & Fundamental Engine.

    Analyzes monetary policy (rates, QE/QT) and fundamental
    drivers (earnings, valuation, sector health) for asset class
    pressure assessment.
    """

    def __init__(self) -> None:
        super().__init__()
        self._fundamental_data: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "monetary_fundamental"

    @property
    def description(self) -> str:
        return "Monetary & fundamental driver analysis (rates, earnings, valuation)"

    def configure(self, **kwargs: Any) -> None:
        self._fundamental_data = kwargs
        self._configured = True

    def analyze(self, data: Dict[str, Any]) -> ScreenerResult:
        if not self._configured:
            return self._not_configured_result()

        # Analyze monetary pressure
        monetary_score = self._analyze_monetary_pressure(data)

        # Analyze fundamental pressure
        fundamental_score = self._analyze_fundamental_pressure(data)

        # Combined score
        combined_score = monetary_score * 0.5 + fundamental_score * 0.5

        direction = (
            ScreenerDirection.BULLISH
            if combined_score > 0.2
            else ScreenerDirection.BEARISH
            if combined_score < -0.2
            else ScreenerDirection.NEUTRAL
        )

        confidence = min(0.85, abs(combined_score) + 0.3)

        return ScreenerResult(
            component_name=self.name,
            direction=direction,
            score=combined_score,
            confidence=confidence,
            details={
                "monetary_score": monetary_score,
                "fundamental_score": fundamental_score,
                "catalyst_calendar": [],
                "fundamental_bias": {
                    "direction": direction.value,
                    "strength": abs(combined_score),
                },
            },
        )

    @staticmethod
    def _analyze_monetary_pressure(data: Dict[str, Any]) -> float:
        """Analyze monetary policy pressure."""
        score = 0.0

        # Interest rate environment
        rates = data.get("interest_rates", {})
        if isinstance(rates, dict):
            rate_change = rates.get("change_3m", 0.0)
            if rate_change < -0.25:
                score += 0.3  # Rate cuts = bullish
            elif rate_change > 0.25:
                score -= 0.3  # Rate hikes = bearish

        # Inflation
        inflation = data.get("inflation", {})
        if isinstance(inflation, dict):
            cpi_yoy = inflation.get("cpi_yoy", 2.5)
            if cpi_yoy < 2.0:
                score += 0.2  # Low inflation = accommodative
            elif cpi_yoy > 4.0:
                score -= 0.2  # High inflation = restrictive

        return max(-1.0, min(1.0, score))

    @staticmethod
    def _analyze_fundamental_pressure(data: Dict[str, Any]) -> float:
        """Analyze fundamental pressure."""
        score = 0.0

        # Earnings growth
        earnings = data.get("earnings", {})
        if isinstance(earnings, dict):
            earnings_growth = earnings.get("yoy_growth", 0.0)
            if earnings_growth > 0.1:
                score += 0.3
            elif earnings_growth < -0.1:
                score -= 0.3

        # Valuation
        valuation = data.get("valuation", {})
        if isinstance(valuation, dict):
            pe_ratio = valuation.get("pe_ratio", 20.0)
            if pe_ratio < 15:
                score += 0.2
            elif pe_ratio > 30:
                score -= 0.2

        return max(-1.0, min(1.0, score))
