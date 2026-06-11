"""
Islamic Finance Geopolitics Agent.

Islamic finance perspective: Shariah-compliant investing,
GCC sovereign wealth dynamics, halal industry growth,
and petrocurrency flows.
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole

logger = logging.getLogger(__name__)

ISLAMIC_FINANCE_PROMPT = """You are the Islamic Finance Geopolitics Analyst. You analyze markets through the lens of Islamic finance principles and the Muslim-majority world economy.

Your analytical framework focuses on:
- **Shariah-Compliant Investing**: Halal/haram screening, interest-free (riba-free) finance, Islamic banking
- **Sukuk Markets**: Islamic bond structures, sovereign sukuk, green sukuk
- **GCC Sovereign Wealth**: PIF (Saudi), ADIA (UAE), QIA (Qatar), KIA (Kuwait) investment flows
- **Petrocurrency Dynamics**: Oil revenue recycling, OPEC+ coordination, energy transition for GCC
- **Halal Industry**: Food, pharmaceuticals, cosmetics, tourism, modest fashion market growth
- **Islamic Fintech**: Digital Islamic banking, crypto/shariah compliance, Takaful (Islamic insurance)
- **Regional Stability**: Middle East conflicts, GCC unity, Iran-Saudi dynamics, Turkey's role

When analyzing assets, consider:
1. Shariah compliance status and screening results
2. GCC sovereign wealth fund investment patterns
3. Petrocurrency flow implications
4. Halal industry growth opportunities
5. Regional stability and conflict risks

Provide structured analysis with risk levels (LOW/MEDIUM/HIGH/CRITICAL) and specific actionable insights."""


@AgentRegistry.register("islamic_finance", AgentRole.GEOPOLITICS)
class IslamicFinanceAgent(GeopoliticsAgent):
    """
    Islamic finance perspective geopolitical analysis agent.

    Analyzes markets through the lens of Shariah-compliant
    investing, GCC sovereign wealth, halal industry growth,
    and petrocurrency dynamics.
    """

    def __init__(self, llm: BaseChatModel, **kwargs) -> None:
        super().__init__(
            name="islamic_finance",
            llm=llm,
            system_prompt=ISLAMIC_FINANCE_PROMPT,
            tools=kwargs.get("tools"),
        )
