"""Peter Lynch Persona — Growth at a reasonable price (GARP) agent."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from quant_nanggroe.agents.personas.base_investor import BaseInvestorAgent

logger = logging.getLogger(__name__)


class PeterLynchAgent(BaseInvestorAgent):
    """Growth at a Reasonable Price (GARP) investor based on Peter Lynch's
    philosophy: invest in what you know, PEG ratio < 1.5, and focus on
    understandable businesses."""

    def __init__(self):
        self.name = "Peter Lynch"
        self.style = "growth_at_reasonable_price"

    def analyze(self, ticker: str, **kwargs) -> Dict[str, Any]:
        """Analyze a stock from Peter Lynch's GARP perspective."""
        return {
            "agent": self.name,
            "style": self.style,
            "ticker": ticker,
            "signal": "neutral",
            "confidence": 0.0,
            "reasoning": (
                f"{self.name} would evaluate {ticker} for PEG ratio < 1.5, "
                "consistent earnings growth, and an understandable business model."
            ),
            "timestamp": datetime.now().isoformat(),
        }
