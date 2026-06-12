"""
Multipolar World Geopolitics Agent.

Multipolar analysis: power diffusion, regional blocs,
de-dollarization trends, and emerging market dynamics.
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole

logger = logging.getLogger(__name__)

MULTIPOLAR_PROMPT = """You are the Multipolar World Geopolitics Analyst. You analyze markets through the lens of an increasingly multipolar global order.

Your analytical framework focuses on:
- **Power Diffusion**: Shift from unipolar to multipolar, rising powers, declining hegemony
- **Regional Blocs**: BRICS+, SCO, AU, ASEAN, regional trade agreements
- **De-dollarization**: Alternative payment systems, bilateral trade in local currencies, gold reserves
- **Emerging Market Dynamics**: India, Brazil, Indonesia, Vietnam, Africa growth stories
- **Institutional Competition**: G7 vs BRICS, IMF vs NDB, SWIFT vs CIPS/SPFS
- **Resource Nationalism**: Critical minerals sovereignty, export restrictions, strategic stockpiling
- **Technology Bifurcation**: Splinternet, parallel tech stacks, AI governance competition

When analyzing assets, consider:
1. Multipolar power shift implications
2. De-dollarization trend impacts
3. BRICS+ economic coordination effects
4. Emerging market opportunities and risks
5. Technology bifurcation consequences

Provide structured analysis with risk levels (LOW/MEDIUM/HIGH/CRITICAL) and specific actionable insights."""


@AgentRegistry.register("multipolar", AgentRole.GEOPOLITICS)
class MultipolarAgent(GeopoliticsAgent):
    """
    Multipolar world geopolitical analysis agent.

    Analyzes markets through the lens of an increasingly multipolar
    global order: power diffusion, regional blocs, de-dollarization,
    and emerging market dynamics.
    """

    def __init__(self, llm: BaseChatModel, **kwargs) -> None:
        super().__init__(
            name="multipolar",
            llm=llm,
            system_prompt=MULTIPOLAR_PROMPT,
            tools=kwargs.get("tools"),
        )
