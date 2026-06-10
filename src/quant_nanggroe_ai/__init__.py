"""
Quant-Nanggroe-AI — Agentic Trading Intelligence OS
====================================================

A production-grade quantitative trading system combining:
- Deterministic engine layer (math, risk, market state)
- Multi-agent AI layer (LangGraph, CrewAI, Pydantic-AI)
- Constitutional risk management (hardcoded limits, veto authority)
- Full audit trail across all decision layers

Merged from 25 repositories including HermesQuantOS and Quant-Nanggroe-AI.
"""

__version__ = "1.0.0"
__author__ = "Quant-Nanggroe-AI Team"

from quant_nanggroe_ai.config import Settings, get_settings
from quant_nanggroe_ai.types import (
    DecisionAction,
    LiquidityLevel,
    MarketRegime,
    MarketState,
    PressureState,
    RiskClearance,
    StrategyStatus,
    VolatilityLevel,
)

__all__ = [
    "DecisionAction",
    "LiquidityLevel",
    "MarketRegime",
    "MarketState",
    "PressureState",
    "RiskClearance",
    "Settings",
    "StrategyStatus",
    "VolatilityLevel",
    "__author__",
    "__version__",
    "get_settings",
]
