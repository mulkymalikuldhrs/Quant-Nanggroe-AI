"""
Multi-Agent Council Package — Structured Debate Systems
========================================================
Bull/Bear and Risk debate modules for multi-perspective
decision-making in the Quant-Nanggroe-AI framework.

Exports:
    BullBearDebate — Bull vs Bear advocate debate with verdict
    RiskDebate     — Aggressive vs Conservative risk level debate

Usage:
    from quant_nanggroe_ai.agents.council import BullBearDebate, RiskDebate

    debate = BullBearDebate()
    verdict = debate.run_debate(bull_args, bear_args, market_data)
"""

from quant_nanggroe_ai.agents.council.bull_bear import (
    BullBearDebate,
    DebateVerdict,
    DebatePosition,
)
from quant_nanggroe_ai.agents.council.risk_debate import (
    RiskDebate,
    RiskDebateResult,
    RiskLevel,
)

__all__ = [
    "BullBearDebate",
    "DebateVerdict",
    "DebatePosition",
    "RiskDebate",
    "RiskDebateResult",
    "RiskLevel",
]
