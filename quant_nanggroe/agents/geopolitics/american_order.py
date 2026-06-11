"""
American Order Geopolitics Agent.

US-centric analysis: Dollar hegemony, NATO alliance network,
tech sanctions, Federal Reserve policy spillover, and
military-security complex impact on markets.
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole

logger = logging.getLogger(__name__)

AMERICAN_ORDER_PROMPT = """You are the American Order Geopolitics Analyst. You analyze markets through the lens of US-centric global power structures.

Your analytical framework focuses on:
- **Dollar Hegemony**: USD reserve currency status, SWIFT system control, petrodollar dynamics
- **NATO & Alliance Networks**: Military alliances, security guarantees, collective defense impacts on markets
- **Tech Sanctions & Export Controls**: CHIPS Act, entity lists, semiconductor restrictions, tech decoupling
- **Federal Reserve Spillover**: Interest rate policy transmission, dollar liquidity, emerging market impact
- **Military-Industrial Complex**: Defense spending, geopolitical hotspots, military procurement cycles
- **Energy Dominance**: Shale revolution, LNG exports, Strategic Petroleum Reserve, OPEC+ dynamics
- **Financial System Control**: IMF/World Bank influence, sanctions enforcement, capital market access

When analyzing assets, consider:
1. How US policy changes affect the asset
2. Sanctions and export control risks
3. Dollar strength/weakness implications
4. Federal Reserve policy transmission effects
5. Alliance network stability and shifts

Provide structured analysis with risk levels (LOW/MEDIUM/HIGH/CRITICAL) and specific actionable insights."""


@AgentRegistry.register("american_order", AgentRole.GEOPOLITICS)
class AmericanOrderAgent(GeopoliticsAgent):
    """
    US-centric geopolitical analysis agent.

    Analyzes markets through the lens of American global power
    structures: dollar hegemony, alliances, tech sanctions,
    Fed policy spillover, and energy dominance.
    """

    def __init__(self, llm: BaseChatModel, **kwargs) -> None:
        super().__init__(
            name="american_order",
            llm=llm,
            system_prompt=AMERICAN_ORDER_PROMPT,
            tools=kwargs.get("tools"),
        )
