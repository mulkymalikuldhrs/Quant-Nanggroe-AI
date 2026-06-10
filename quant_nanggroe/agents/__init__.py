"""
Quant Nanggroe AI Agents Package.

Complete agent framework for the Quant Nanggroe AI Trading Intelligence OS.
Uses LangGraph for orchestration with 9 specialized agent types and a
council debate system.

v2 enhancements:
- Multi-path asset-class conditional routing
- ATR-based position sizing with TP1/TP2/TP3 geometry
- Portfolio concentration/correlation/Kelly validation
- Smart order routing with venue scoring
- Human-in-the-loop checkpoint for high-risk trades
"""

from quant_nanggroe.agents.base import BaseAgent, create_llm
from quant_nanggroe.agents.state import (
    AgentOutput,
    AgentRole,
    AgentState,
    AssetClass,
    CouncilResult,
    Decision,
    DebateState,
    MarketData,
    MarketRegime,
    PortfolioState,
    PortfolioValidation,
    PositionInfo,
    PositionSizingResult,
    RiskAssessment,
    RiskCheckpoint,
    RiskDebateState,
    RiskVerdict,
    Signal,
    SignalDirection,
    SmartOrderRouting,
    TradeAction,
    VenueScore,
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
from quant_nanggroe.agents.graph_v2 import TradingGraphV2
from quant_nanggroe.agents.registry import AgentFactory, AgentRegistry

# v2 Node modules
from quant_nanggroe.agents.nodes import (
    AssetRouter,
    detect_asset_class,
    route_by_asset_class,
    PositionSizer,
    compute_atr_position_sizing,
    PortfolioValidator,
    validate_portfolio,
    SmartExecutor,
    route_order_smart,
    HumanCheckpoint,
    check_human_approval,
)

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
    # State
    "AgentOutput",
    "AgentRole",
    "AgentState",
    "AssetClass",
    "CouncilResult",
    "Decision",
    "DebateState",
    "MarketData",
    "MarketRegime",
    "PortfolioState",
    "PortfolioValidation",
    "PositionInfo",
    "PositionSizingResult",
    "RiskAssessment",
    "RiskCheckpoint",
    "RiskDebateState",
    "RiskVerdict",
    "Signal",
    "SignalDirection",
    "SmartOrderRouting",
    "TradeAction",
    "VenueScore",
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
    "TradingGraphV2",
    # Registry
    "AgentFactory",
    "AgentRegistry",
    # v2 Node modules
    "AssetRouter",
    "detect_asset_class",
    "route_by_asset_class",
    "PositionSizer",
    "compute_atr_position_sizing",
    "PortfolioValidator",
    "validate_portfolio",
    "SmartExecutor",
    "route_order_smart",
    "HumanCheckpoint",
    "check_human_approval",
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
