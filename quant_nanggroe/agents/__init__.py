"""
Quant Nanggroe AI Agents Package.

Complete agent framework for the Quant Nanggroe AI Trading Intelligence OS.
Uses LangGraph for orchestration with 9 specialized agent types and a
council debate system.
"""

from quant_nanggroe.agents.base import BaseAgent, create_llm
from quant_nanggroe.agents.state import (
    AgentOutput,
    AgentRole,
    AgentState,
    CouncilResult,
    Decision,
    DebateState,
    MarketData,
    MarketRegime,
    PortfolioState,
    PositionInfo,
    RiskAssessment,
    RiskCheckpoint,
    RiskDebateState,
    RiskVerdict,
    Signal,
    SignalDirection,
    TradeAction,
    VoteResult,
    create_initial_state,
    # Constitutional limits (HARDCODED - NO OVERRIDE)
    MAX_RISK_PER_TRADE,
    MAX_DAILY_LOSS,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
    MAX_CORRELATED_POSITIONS,
    MAX_POSITION_SIZE_PCT,
    MAX_LEVERAGE,
    MAX_DRAWDOWN_PCT,
    MAX_TRADES_PER_DAY,
    CONFIDENCE_THRESHOLD,
)
from quant_nanggroe.agents.chinese_wall import ChineseWall, ChineseWallError
from quant_nanggroe.agents.graph import TradingGraph
from quant_nanggroe.agents.registry import AgentFactory, AgentRegistry

# Agent classes
from quant_nanggroe.agents.researcher.agent import ResearcherAgent
from quant_nanggroe.agents.trader.agent import TraderAgent
from quant_nanggroe.agents.strategist.agent import StrategistAgent
from quant_nanggroe.agents.risk.agent import RiskAgent
from quant_nanggroe.agents.portfolio.agent import PortfolioAgent
from quant_nanggroe.agents.execution.agent import ExecutionAgent
from quant_nanggroe.agents.macro.agent import MacroAgent
from quant_nanggroe.agents.crypto.agent import CryptoAgent
from quant_nanggroe.agents.forex.agent import ForexAgent
from quant_nanggroe.agents.compliance.agent import ComplianceAgent, ComplianceVerdict

# Council components
from quant_nanggroe.agents.council.debate import CouncilDebate
from quant_nanggroe.agents.council.voting import CouncilVoting

# Debate engine
from quant_nanggroe.agents.debate_engine import DebateEngine
from quant_nanggroe.agents.debate.reflection import Reflector, SignalProcessor
from quant_nanggroe.agents.debate.research_debate import BullResearcherNode, BearResearcherNode
from quant_nanggroe.agents.debate.risk_debate import ConservativeDebatorNode, NeutralDebatorNode, AggressiveDebatorNode

# Geopolitics
from quant_nanggroe.agents.geopolitics.base import GeopoliticsAgent

# Gold trader
from quant_nanggroe.agents.gold_trader import GoldTrader

# Marketplace
from quant_nanggroe.agents.marketplace import AgentMarketplace

# Personas
from quant_nanggroe.agents.personas.base_investor import BaseInvestorAgent

# Protocols
from quant_nanggroe.agents.protocols import ProtocolAdapter, MCPAdapter

# Smart Money Concepts
from quant_nanggroe.agents.smc.enhanced import SmartMoneyAgent, OrderBlockDetector, FairValueGapDetector

__all__ = [
    # Base
    "BaseAgent",
    "create_llm",
    # Chinese Wall
    "ChineseWall",
    "ChineseWallError",
    # State
    "AgentOutput",
    "AgentRole",
    "AgentState",
    "CouncilResult",
    "Decision",
    "DebateState",
    "MarketData",
    "MarketRegime",
    "PortfolioState",
    "PositionInfo",
    "RiskAssessment",
    "RiskCheckpoint",
    "RiskDebateState",
    "RiskVerdict",
    "Signal",
    "SignalDirection",
    "TradeAction",
    "VoteResult",
    "create_initial_state",
    # Constitutional limits
    "MAX_RISK_PER_TRADE",
    "MAX_DAILY_LOSS",
    "MAX_WEEKLY_LOSS",
    "MIN_RISK_REWARD",
    "MAX_CORRELATED_POSITIONS",
    "MAX_POSITION_SIZE_PCT",
    "MAX_LEVERAGE",
    "MAX_DRAWDOWN_PCT",
    "MAX_TRADES_PER_DAY",
    "CONFIDENCE_THRESHOLD",
    # Graph
    "TradingGraph",
    # Registry
    "AgentFactory",
    "AgentRegistry",
    # Agents
    "ResearcherAgent",
    "TraderAgent",
    "StrategistAgent",
    "RiskAgent",
    "PortfolioAgent",
    "ExecutionAgent",
    "MacroAgent",
    "CryptoAgent",
    "ForexAgent",
    "ComplianceAgent",
    "ComplianceVerdict",
    # Council
    "CouncilDebate",
    "CouncilVoting",
    # Debates
    "DebateEngine",
    "Reflector",
    "SignalProcessor",
    "BullResearcherNode",
    "BearResearcherNode",
    "ConservativeDebatorNode",
    "NeutralDebatorNode",
    "AggressiveDebatorNode",
    # Geopolitics
    "GeopoliticsAgent",
    # Gold
    "GoldTrader",
    # Marketplace
    "AgentMarketplace",
    # Personas
    "BaseInvestorAgent",
    # Protocols
    "ProtocolAdapter",
    "MCPAdapter",
    # Smart Money Concepts
    "SmartMoneyAgent",
    "OrderBlockDetector",
    "FairValueGapDetector",
]
