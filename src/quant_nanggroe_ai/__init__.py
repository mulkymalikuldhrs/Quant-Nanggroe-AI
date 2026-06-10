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

from quant_nanggroe_ai.config import get_settings, Settings
from quant_nanggroe_ai.types import (
    MarketRegime,
    VolatilityLevel,
    LiquidityLevel,
    RiskClearance,
    DecisionAction,
    StrategyStatus,
    PressureState,
    MarketState,
)

__all__ = [
    "__version__",
    "__author__",
    "get_settings",
    "Settings",
    "MarketRegime",
    "VolatilityLevel",
    "LiquidityLevel",
    "RiskClearance",
    "DecisionAction",
    "StrategyStatus",
    "PressureState",
    "MarketState",
]
