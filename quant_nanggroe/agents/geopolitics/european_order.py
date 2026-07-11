"""
Geopolitics Agent — European Order (Regulatory Superpower) Analysis.
"""

from __future__ import annotations

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole


@AgentRegistry.register("european_order", AgentRole.GEOPOLITICS)
class EuropeanOrderAgent(GeopoliticsAgent):
    """Analyses geopolitical trends through the European-led international order lens."""

    def __init__(self, llm):
        super().__init__(
            name="european_order",
            llm=llm,
            system_prompt=(
                "You are EuropeanOrderAgent, a geopolitical analyst specialising in the "
                "European-led international order. Your distinguishing lens is the EU's role "
                "as a Regulatory Superpower — analyse how European standards (GDPR, CSRD, "
                "CBAM, MiCA, supply-chain due diligence) extraterritorially shape global "
                "corporate behaviour, trade compliance costs, and capital allocation. Assess "
                "NATO deterrence posture, EU enlargement dynamics, energy transition "
                "imperatives, migration pressure, and the bloc's pursuit of strategic autonomy "
                "from both the US and China. Provide structured, data-driven geopolitical "
                "risk assessments with explicit confidence levels."
            ),
        )
