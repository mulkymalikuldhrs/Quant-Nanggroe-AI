"""Agent Debate System — Structured multi-round investment debate.

Implements LangGraph-based debate between Bull/Bear researchers
and Conservative/Neutral/Aggressive risk debators, with reflection
and signal extraction. Ported from TradingAgents and enhanced.
"""

from quant_nanggroe.agents.debate.research_debate import (
    BullResearcherNode,
    BearResearcherNode,
    InvestmentDebateState,
)
from quant_nanggroe.agents.debate.risk_debate import (
    ConservativeDebatorNode,
    NeutralDebatorNode,
    AggressiveDebatorNode,
    RiskDebateState,
)
from quant_nanggroe.agents.debate.graph import TradingDebateGraph

__all__ = [
    "BullResearcherNode",
    "BearResearcherNode",
    "InvestmentDebateState",
    "ConservativeDebatorNode",
    "NeutralDebatorNode",
    "AggressiveDebatorNode",
    "RiskDebateState",
    "TradingDebateGraph",
]
