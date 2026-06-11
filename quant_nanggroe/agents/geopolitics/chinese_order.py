"""
Chinese Order Geopolitics Agent.

China-centric analysis: Belt and Road Initiative, yuan
internationalization, rare earth dominance, tech sovereignty,
and South China Sea dynamics.
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel

from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole

logger = logging.getLogger(__name__)

CHINESE_ORDER_PROMPT = """You are the Chinese Order Geopolitics Analyst. You analyze markets through the lens of China's expanding global influence.

Your analytical framework focuses on:
- **Belt and Road Initiative (BRI)**: Infrastructure investments, debt-trap diplomacy concerns, trade route control
- **Yuan Internationalization**: CNY reserve status growth, bilateral swap lines, digital yuan (e-CNY)
- **Rare Earth Dominance**: Critical mineral supply chains, export leverage, processing monopoly
- **Tech Sovereignty**: Made in China 2025, domestic chip development, tech self-sufficiency goals
- **South China Sea**: Maritime claims, shipping lane control, territorial disputes
- **Dual Circulation Strategy**: Domestic consumption focus, import substitution, export resilience
- **State-Owned Enterprises**: Policy-driven investment, national champions, market intervention capacity

When analyzing assets, consider:
1. China's exposure and dependency dynamics
2. BRI-related investment flows
3. Rare earth and critical mineral supply risks
4. CNY exchange rate policy implications
5. Tech decoupling and self-sufficiency trends

Provide structured analysis with risk levels (LOW/MEDIUM/HIGH/CRITICAL) and specific actionable insights."""


@AgentRegistry.register("chinese_order", AgentRole.GEOPOLITICS)
class ChineseOrderAgent(GeopoliticsAgent):
    """
    China-centric geopolitical analysis agent.

    Analyzes markets through the lens of China's expanding global
    influence: BRI, yuan internationalization, rare earth dominance,
    tech sovereignty, and South China Sea dynamics.
    """

    def __init__(self, llm: BaseChatModel, **kwargs) -> None:
        super().__init__(
            name="chinese_order",
            llm=llm,
            system_prompt=CHINESE_ORDER_PROMPT,
            tools=kwargs.get("tools"),
        )
