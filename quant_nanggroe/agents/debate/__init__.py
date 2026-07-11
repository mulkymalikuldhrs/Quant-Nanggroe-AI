"""Agent Debate System — Structured multi-round investment debate.

Implements LangGraph-based debate between Bull/Bear researchers
and Conservative/Neutral/Aggressive risk debators, with reflection
and signal extraction. Ported from TradingAgents and enhanced.
"""

from quant_nanggroe.agents.debate.council_logger import (
    CouncilDecision,
    CouncilDecisionLogger,
)
from quant_nanggroe.agents.debate.engine import (
    AgentOpinion,
    DebateEngine,
    DebateResult,
    RiskManager,
    RiskMetrics,
    Signal,
)
from quant_nanggroe.agents.debate.reflection import SignalProcessor
from quant_nanggroe.agents.debate.research_debate import (
    BearResearcherNode,
    BullResearcherNode,
    InvestmentDebateState,
)
from quant_nanggroe.agents.debate.risk_debate import (
    AggressiveDebatorNode,
    ConservativeDebatorNode,
    NeutralDebatorNode,
    RiskDebateState,
)

# Council decision log singleton
council_logger = CouncilDecisionLogger()

__all__ = [
    # Research debate
    "BullResearcherNode",
    "BearResearcherNode",
    "InvestmentDebateState",
    # Risk debate
    "ConservativeDebatorNode",
    "NeutralDebatorNode",
    "AggressiveDebatorNode",
    "RiskDebateState",
    # Engine
    "Signal",
    "AgentOpinion",
    "RiskMetrics",
    "RiskManager",
    "DebateEngine",
    # Council logging
    "CouncilDecision",
    "CouncilDecisionLogger",
    "council_logger",
    # Reflection
    "SignalProcessor",
]
