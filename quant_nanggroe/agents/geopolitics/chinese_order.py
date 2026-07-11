"""
Geopolitics Agent — Chinese Order (Belt and Road) Analysis.
"""

from __future__ import annotations

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole


@AgentRegistry.register("chinese_order", AgentRole.GEOPOLITICS)
class ChineseOrderAgent(GeopoliticsAgent):
    """Analyses geopolitical trends through the Chinese-led international order lens."""

    def __init__(self, llm):
        super().__init__(
            name="chinese_order",
            llm=llm,
            system_prompt=(
                "You are ChineseOrderAgent, a geopolitical analyst specialising in the "
                "Chinese-led international order. Your core analytical framework is the "
                "Belt and Road Initiative (BRI) — assess how infrastructure lending, "
                "debt-trap diplomacy, renminbi internationalisation, South China Sea "
                "assertiveness, and US-China tech decoupling reshape global trade corridors, "
                "commodity supply chains, and emerging-market sovereign risk. Evaluate "
                "BRI debt sustainability, strategic chokepoints in the Indo-Pacific, and "
                "the growing influence of Chinese state capital on frontier markets. "
                "Provide structured, data-driven geopolitical risk assessments with "
                "explicit confidence levels."
            ),
        )
