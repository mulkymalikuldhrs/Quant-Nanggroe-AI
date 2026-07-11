"""
Warren Buffett Persona — Value investing agent persona.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from quant_nanggroe.agents.personas.base_investor import BaseInvestorAgent

logger = logging.getLogger(__name__)


class WarrenBuffettAgent(BaseInvestorAgent):
    """Investment analysis persona based on Warren Buffett's philosophy.

    Focuses on:
    - Economic moats (competitive advantages)
    - Intrinsic value vs market price
    - Long-term holding period
    - Circle of competence
    - Management quality
    """

    def __init__(self):
        self.name = "Warren Buffett"
        self.style = "value_investing"
        self.holding_period_years = 10

    def estimate_intrinsic_value(
        self,
        ticker: str,
        free_cash_flow: float,
        growth_rate: float = 0.05,
        discount_rate: float = 0.10,
        years: int = 10,
    ) -> float:
        """Estimate intrinsic value using discounted cash flow."""
        if discount_rate <= 0:
            return free_cash_flow * years
        total = 0.0
        for y in range(1, years + 1):
            fcf = free_cash_flow * ((1 + growth_rate) ** y)
            total += fcf / ((1 + discount_rate) ** y)
        return total

    def assess_moat(self, ticker: str, industry: str, moat_factors: Dict[str, bool]) -> str:
        """Assess economic moat based on qualitative factors."""
        score = sum(1 for v in moat_factors.values() if v)
        if score >= 4:
            return "wide"
        elif score >= 2:
            return "narrow"
        return "none"

    def analyze(self, ticker: str, price: float, intrinsic_value: float) -> Dict[str, Any]:
        """Produce a full investment thesis as a dict."""
        moa = (intrinsic_value - price) / price if price > 0 else 0.0
        return {
            "agent": self.name,
            "style": self.style,
            "ticker": ticker,
            "moat_rating": "narrow",
            "intrinsic_value": intrinsic_value,
            "current_price": price,
            "margin_of_safety": moa,
            "signal": "bullish" if moa > 0.2 else "neutral",
            "confidence": min(moa, 1.0),
            "reasoning": (
                f"{ticker} at ${price:.2f} vs intrinsic ${intrinsic_value:.2f} ({moa * 100:.1f}% margin of safety)"
            ),
            "timestamp": datetime.now().isoformat(),
        }
