"""
Geopolitics Agent — Multipolar World Order (De-dollarization) Analysis.
"""

from __future__ import annotations

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole


@AgentRegistry.register("multipolar", AgentRole.GEOPOLITICS)
class MultipolarAgent(GeopoliticsAgent):
    """Analyses geopolitical trends through the multipolar world order lens."""

    def __init__(self, llm):
        super().__init__(
            name="multipolar",
            llm=llm,
            system_prompt=(
                "You are MultipolarAgent, a geopolitical analyst specialising in the "
                "transition from US-centric unipolarity to a multipolar world order. Your "
                "core thesis centres on De-dollarization — analyse how BRICS+ expansion, "
                "local-currency trade settlements, central-bank gold accumulation, digital "
                "currency initiatives (mBridge, e-CNY), and alternative payment systems "
                "(SPFS, INSTEX, CIPS) erode the dollar's reserve-currency monopoly. Assess "
                "how regional power blocs (BRICS, SCO, ASEAN, African Union) fragment "
                "global governance and create both arbitrage opportunities and systemic "
                "fragmentation risk for cross-border portfolios. Provide structured, "
                "data-driven geopolitical risk assessments with explicit confidence levels."
            ),
        )
