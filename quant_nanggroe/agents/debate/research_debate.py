"""Research Debate — Bull vs Bear structured investment debate.

Implements the Bull/Bear researcher debate pattern from TradingAgents,
where two opposing researchers present arguments for/against an
investment thesis, then the debate outcome feeds into risk assessment.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


class DebateArgument(BaseModel):
    """A single argument in the debate."""
    agent: str = ""
    stance: str = ""  # "bull" or "bear"
    points: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    key_evidence: List[str] = Field(default_factory=list)
    counter_points: List[str] = Field(default_factory=list)


class InvestmentDebateState(TypedDict, total=False):
    """State for the investment debate graph."""
    symbol: str
    market_data: Dict[str, Any]
    bull_arguments: List[DebateArgument]
    bear_arguments: List[DebateArgument]
    debate_round: int
    max_rounds: int
    bull_score: float
    bear_score: float
    consensus_reached: bool
    final_verdict: str
    key_factors: List[str]


BULL_SYSTEM_PROMPT = """You are a BULL researcher analyzing {symbol}.
Your job is to present compelling arguments FOR investing in this asset.

Focus on:
1. Strong fundamentals and growth prospects
2. Positive technical indicators and momentum
3. Favorable market conditions and catalysts
4. Competitive advantages and market position
5. Upside potential and favorable risk/reward

Always provide evidence-based arguments with specific data points.
Rate your confidence from 0.0 to 1.0.
Acknowledge valid bear points but explain why bulls outweigh them.
"""

BEAR_SYSTEM_PROMPT = """You are a BEAR researcher analyzing {symbol}.
Your job is to present compelling arguments AGAINST investing in this asset.

Focus on:
1. Fundamental weaknesses and declining metrics
2. Negative technical signals and bearish patterns
3. Unfavorable market conditions and headwinds
4. Competitive threats and market risks
5. Downside risks and unfavorable risk/reward

Always provide evidence-based arguments with specific data points.
Rate your confidence from 0.0 to 1.0.
Acknowledge valid bull points but explain why bears outweigh them.
"""


class BullResearcherNode:
    """Bull researcher node for investment debate.

    Generates arguments in favor of the investment thesis.
    """

    def __init__(self, llm: Any = None) -> None:
        self._llm = llm
        self.name = "bull_researcher"

    async def run(self, state: InvestmentDebateState) -> InvestmentDebateState:
        """Generate bull arguments for the investment."""
        symbol = state.get("symbol", "UNKNOWN")
        round_num = state.get("debate_round", 0) + 1

        # In production, this would call LLM
        # For now, create structured analysis from market data
        market_data = state.get("market_data", {})
        price = market_data.get("price", 0)
        change_pct = market_data.get("change_pct", 0)

        # Build bull argument
        points = []
        evidence = []

        if change_pct > 0:
            points.append(f"Positive momentum: {change_pct:.1f}% recent gain")
            evidence.append(f"Price trend: {price}")

        if market_data.get("volume_trend") == "increasing":
            points.append("Volume confirms price movement")
            evidence.append("Rising volume on up days")

        # Add default bull points
        points.extend([
            "Strong market positioning",
            "Favorable macro environment",
            "Technical breakout potential",
        ])
        evidence.extend([
            "Sector outperformance",
            "Central bank policy support",
            "Key resistance levels broken",
        ])

        # Counter bear arguments if they exist
        counter_points = []
        for bear_arg in state.get("bear_arguments", []):
            for point in bear_arg.points[:2]:
                counter_points.append(f"Counter to bear: {point} - bullish context applies")

        argument = DebateArgument(
            agent="bull_researcher",
            stance="bull",
            points=points,
            confidence=0.7,
            key_evidence=evidence,
            counter_points=counter_points,
        )

        state["bull_arguments"] = state.get("bull_arguments", []) + [argument]
        state["debate_round"] = round_num

        # Update score
        total_bull = sum(a.confidence for a in state["bull_arguments"])
        total_bear = sum(a.confidence for a in state.get("bear_arguments", []))
        total = total_bull + total_bear
        state["bull_score"] = total_bull / max(total, 1.0)
        state["bear_score"] = total_bear / max(total, 1.0)

        # Check consensus
        if round_num >= state.get("max_rounds", 3):
            state["consensus_reached"] = True
            state["final_verdict"] = "BULLISH" if state["bull_score"] > state["bear_score"] else "BEARISH"

        return state


class BearResearcherNode:
    """Bear researcher node for investment debate.

    Generates arguments against the investment thesis.
    """

    def __init__(self, llm: Any = None) -> None:
        self._llm = llm
        self.name = "bear_researcher"

    async def run(self, state: InvestmentDebateState) -> InvestmentDebateState:
        """Generate bear arguments against the investment."""
        symbol = state.get("symbol", "UNKNOWN")
        round_num = state.get("debate_round", 0)

        market_data = state.get("market_data", {})
        price = market_data.get("price", 0)
        change_pct = market_data.get("change_pct", 0)

        points = []
        evidence = []

        if change_pct < 0:
            points.append(f"Negative momentum: {change_pct:.1f}% recent decline")
            evidence.append(f"Price trend: {price}")

        if market_data.get("volatility") == "high":
            points.append("High volatility increases downside risk")
            evidence.append("Elevated VIX / implied volatility")

        points.extend([
            "Potential overvaluation risk",
            "Macro headwinds possible",
            "Key support levels at risk",
        ])
        evidence.extend([
            "Elevated P/E ratio",
            "Rising interest rate expectations",
            "Technical indicators showing weakness",
        ])

        counter_points = []
        for bull_arg in state.get("bull_arguments", []):
            for point in bull_arg.points[:2]:
                counter_points.append(f"Counter to bull: {point} - bearish context applies")

        argument = DebateArgument(
            agent="bear_researcher",
            stance="bear",
            points=points,
            confidence=0.6,
            key_evidence=evidence,
            counter_points=counter_points,
        )

        state["bear_arguments"] = state.get("bear_arguments", []) + [argument]

        # Update score
        total_bull = sum(a.confidence for a in state.get("bull_arguments", []))
        total_bear = sum(a.confidence for a in state["bear_arguments"])
        total = total_bull + total_bear
        state["bull_score"] = total_bull / max(total, 1.0)
        state["bear_score"] = total_bear / max(total, 1.0)

        return state


__all__ = [
    "DebateArgument",
    "InvestmentDebateState",
    "BullResearcherNode",
    "BearResearcherNode",
    "BULL_SYSTEM_PROMPT",
    "BEAR_SYSTEM_PROMPT",
]
