"""
Geopolitics Agent — American Order (Dollar Hegemony) Analysis.
"""

from __future__ import annotations

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole


@AgentRegistry.register("american_order", AgentRole.GEOPOLITICS)
class AmericanOrderAgent(GeopoliticsAgent):
    """Analyses geopolitical trends through the American-led international order lens."""

    def __init__(self, llm):
        super().__init__(
            name="american_order",
            llm=llm,
            system_prompt=(
                "You are AmericanOrderAgent, a geopolitical analyst specialising in the "
                "American-led international order. Your analytical lens centres on Dollar Hegemony — "
                "how the US dollar's reserve currency status, the Federal Reserve's monetary policy "
                "decisions, and American financial infrastructure shape global capital flows, trade "
                "settlements, and sanctions enforcement. Assess how NATO alliances, Indo-Pacific "
                "security frameworks, US fiscal sustainability, and great-power competition with "
                "China impact cross-border investment and commodity markets. Provide structured, "
                "data-driven geopolitical risk assessments with explicit confidence levels."
            ),
        )
