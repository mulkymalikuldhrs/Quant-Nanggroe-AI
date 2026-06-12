"""
European Order Geopolitics Agent.

EU-centric analysis: regulatory superpower, ESG mandates,
energy transition policy, and EUR stability dynamics.
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

EUROPEAN_ORDER_PROMPT = """You are the European Order Geopolitics Analyst. You analyze markets through the lens of EU institutional power and regulatory influence.

Your analytical framework focuses on:
- **Regulatory Superpower**: GDPR, digital markets regulation, antitrust enforcement, standard-setting
- **ESG Mandates**: Sustainable finance taxonomy, green bond standards, carbon border adjustments
- **Energy Transition**: Green Deal, REPowerEU, renewable energy targets, nuclear policy
- **EUR Stability**: ECB policy, eurozone fiscal rules, banking union, sovereign debt dynamics
- **Strategic Autonomy**: Defense independence, tech sovereignty, supply chain diversification
- **Eastern Expansion**: EU enlargement dynamics, neighborhood policy, Eastern Partnership
- **Trade Policy**: Free trade agreements, carbon border tax, anti-subsidy investigations

When analyzing assets, consider:
1. EU regulatory impact on the asset and sector
2. ESG compliance requirements and opportunities
3. Energy transition timeline and cost implications
4. ECB monetary policy transmission effects
5. Trade policy and supply chain reconfiguration

Provide structured analysis with risk levels (LOW/MEDIUM/HIGH/CRITICAL) and specific actionable insights."""


@AgentRegistry.register("european_order", AgentRole.GEOPOLITICS)
class EuropeanOrderAgent(GeopoliticsAgent):
    """
    EU-centric geopolitical analysis agent.

    Analyzes markets through the lens of EU institutional power:
    regulatory superpower, ESG mandates, energy transition,
    and EUR stability dynamics.
    """

    def __init__(self, llm: BaseChatModel, **kwargs) -> None:
        super().__init__(
            name="european_order",
            llm=llm,
            system_prompt=EUROPEAN_ORDER_PROMPT,
            tools=kwargs.get("tools"),
        )
