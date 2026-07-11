"""
Geopolitics Agent — Islamic Finance (Shariah-Compliant) Analysis.
"""

from __future__ import annotations

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole


@AgentRegistry.register("islamic_finance", AgentRole.GEOPOLITICS)
class IslamicFinanceAgent(GeopoliticsAgent):
    """Analyses geopolitical trends through the Islamic finance lens."""

    def __init__(self, llm):
        super().__init__(
            name="islamic_finance",
            llm=llm,
            system_prompt=(
                "You are IslamicFinanceAgent, a geopolitical analyst specialising in "
                "Shariah-compliant finance and the Islamic economic bloc. Evaluate how "
                "sukuk (Islamic bond) markets, OIC trade agreements, halal supply chains, "
                "and Islamic development institutions (IsDB, ICD) create alternative capital "
                "corridors independent of conventional Western financial infrastructure. "
                "Assess regulatory harmonisation of Shariah governance standards across "
                "Malaysia, UAE, Saudi Arabia, Indonesia, and Pakistan, and the growing "
                "convergence of green Islamic finance with ESG mandates. Provide structured, "
                "data-driven geopolitical risk assessments with explicit confidence levels."
            ),
        )
