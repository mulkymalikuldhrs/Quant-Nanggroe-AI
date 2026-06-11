"""
Quant Nanggroe AI Agents Package.

Complete agent framework for the Quant Nanggroe AI Trading Intelligence OS.
Uses LangGraph for orchestration with 9 specialized agent types and a
council debate system.

Type Resolution:
- Pipeline types (Signal, Decision, RiskAssessment, MarketData) are
  LangGraph state-specific wrappers used in the agent graph.
- Canonical types live in quant_nanggroe.types.* and are for domain modelling.
- For canonical types, import from quant_nanggroe.types.* directly.
"""

from quant_nanggroe.agents.base import BaseAgent, create_llm
from quant_nanggroe.agents.state import (
    # Pipeline-specific types
    Signal,
    Decision,
    RiskAssessment,
    MarketData,
    # Agent-specific types (not duplicated in types/)
    AgentRole,
    AgentState,
    AgentOutput,
    CouncilResult,
    DebateState,
    MarketRegime,
    PortfolioState,
    PositionInfo,
    RiskCheckpoint,
    RiskDebateState,
    RiskVerdict,
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

# Council components
from quant_nanggroe.agents.council.debate import CouncilDebate
from quant_nanggroe.agents.council.voting import CouncilVoting

__all__ = [
    # Base
    "BaseAgent",
    "create_llm",
    # Pipeline-specific types
    "Signal",
    "Decision",
    "RiskAssessment",
    "MarketData",
    # Agent-specific types (not duplicated)
    "AgentRole",
    "AgentState",
    "AgentOutput",
    "CouncilResult",
    "DebateState",
    "MarketRegime",
    "PortfolioState",
    "PositionInfo",
    "RiskCheckpoint",
    "RiskDebateState",
    "RiskVerdict",
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
    # Council
    "CouncilDebate",
    "CouncilVoting",
]
