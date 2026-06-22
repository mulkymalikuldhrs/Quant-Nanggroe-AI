"""Quant Nanggroe AI Agents Package.

Complete agent framework for the Quant Nanggroe AI Trading Intelligence OS.
Uses LangGraph for orchestration with 9 specialized agent types and a
council debate system.

Uses lazy imports to avoid circular dependencies and speed up module loading.
"""

from __future__ import annotations

import importlib
from typing import Any

_module_registry = {
    "BaseAgent": ".base",
    "create_llm": ".base",
    "AgentOutput": ".state",
    "AgentRole": ".state",
    "AgentState": ".state",
    "CouncilResult": ".state",
    "Decision": ".state",
    "DebateState": ".state",
    "MarketData": ".state",
    "MarketRegime": ".state",
    "PortfolioState": ".state",
    "PositionInfo": ".state",
    "RiskAssessment": ".state",
    "RiskCheckpoint": ".state",
    "RiskDebateState": ".state",
    "RiskVerdict": ".state",
    "Signal": ".state",
    "SignalDirection": ".state",
    "TradeAction": ".state",
    "VoteResult": ".state",
    "create_initial_state": ".state",
    "MAX_RISK_PER_TRADE": ".state",
    "MAX_DAILY_LOSS": ".state",
    "MAX_WEEKLY_LOSS": ".state",
    "MIN_RISK_REWARD": ".state",
    "MAX_CORRELATED_POSITIONS": ".state",
    "MAX_POSITION_SIZE_PCT": ".state",
    "MAX_LEVERAGE": ".state",
    "MAX_DRAWDOWN_PCT": ".state",
    "MAX_TRADES_PER_DAY": ".state",
    "CONFIDENCE_THRESHOLD": ".state",
    "TradingGraph": ".graph",
    "AgentFactory": ".registry",
    "AgentRegistry": ".registry",
    "ResearcherAgent": ".researcher.agent",
    "TraderAgent": ".trader.agent",
    "StrategistAgent": ".strategist.agent",
    "RiskAgent": ".risk.agent",
    "PortfolioAgent": ".portfolio.agent",
    "ExecutionAgent": ".execution.agent",
    "MacroAgent": ".macro.agent",
    "CryptoAgent": ".crypto.agent",
    "ForexAgent": ".forex.agent",
    "CouncilDebate": ".council.debate",
    "CouncilVoting": ".council.voting",
}

__all__ = sorted(_module_registry.keys())


def __getattr__(name: str) -> Any:
    if name not in _module_registry:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path = _module_registry[name]
    mod = importlib.import_module(module_path, package=__name__)
    attr = getattr(mod, name)
    globals()[name] = attr
    return attr
