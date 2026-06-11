"""Risk Debate — Conservative/Neutral/Aggressive risk debate trio.

Implements the three-way risk debate pattern from TradingAgents,
where risk analysts with different risk appetites debate the
appropriate risk level for a trade.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


class RiskPosition(BaseModel):
    """A risk debator's position on a trade."""
    debator: str = ""
    risk_stance: str = ""  # conservative, neutral, aggressive
    max_position_pct: float = 0.0
    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    reasoning: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class RiskDebateState(TypedDict, total=False):
    """State for the risk debate."""
    symbol: str
    trade_direction: str
    proposed_size: float
    current_portfolio: Dict[str, Any]
    conservative_position: Optional[RiskPosition]
    neutral_position: Optional[RiskPosition]
    aggressive_position: Optional[RiskPosition]
    debate_round: int
    final_risk_level: str  # low, medium, high
    approved_size: float
    risk_score: float
    conditions: List[str]


class ConservativeDebatorNode:
    """Conservative risk debator — prioritizes capital preservation.

    Advocates for smaller positions, tighter stop losses,
    and more stringent risk limits.
    """

    def __init__(self) -> None:
        self.name = "conservative_debator"

    async def run(self, state: RiskDebateState) -> RiskDebateState:
        """Generate conservative risk position."""
        proposed = state.get("proposed_size", 0)
        portfolio = state.get("current_portfolio", {})
        total_equity = portfolio.get("total_equity", 100000)

        # Conservative: 0.5% risk per trade max
        max_position = total_equity * 0.005
        approved_size = min(proposed, max_position)

        position = RiskPosition(
            debator="conservative",
            risk_stance="conservative",
            max_position_pct=0.5,
            stop_loss_pct=1.0,
            take_profit_pct=2.0,
            reasoning=[
                "Capital preservation is paramount",
                "Market uncertainty warrants caution",
                "Smaller positions reduce portfolio impact",
            ],
            concerns=[
                "Current market volatility elevated",
                "Portfolio concentration risk",
                "Black swan event possibility",
            ],
            confidence=0.8,
        )

        state["conservative_position"] = position
        state["approved_size"] = approved_size
        return state


class NeutralDebatorNode:
    """Neutral risk debator — balanced risk/reward approach.

    Advocates for moderate positions, standard risk limits,
    and balanced stop loss/take profit levels.
    """

    def __init__(self) -> None:
        self.name = "neutral_debator"

    async def run(self, state: RiskDebateState) -> RiskDebateState:
        """Generate neutral risk position."""
        proposed = state.get("proposed_size", 0)
        portfolio = state.get("current_portfolio", {})
        total_equity = portfolio.get("total_equity", 100000)

        # Neutral: 1% risk per trade
        max_position = total_equity * 0.01
        approved_size = min(proposed, max_position)

        position = RiskPosition(
            debator="neutral",
            risk_stance="neutral",
            max_position_pct=1.0,
            stop_loss_pct=2.0,
            take_profit_pct=4.0,
            reasoning=[
                "Balanced risk/reward approach",
                "Standard position sizing appropriate",
                "Diversification maintained",
            ],
            concerns=[
                "Position size within acceptable range",
                "Risk/reward ratio favorable",
                "Correlation with existing positions",
            ],
            confidence=0.65,
        )

        state["neutral_position"] = position
        return state


class AggressiveDebatorNode:
    """Aggressive risk debator — maximizes potential returns.

    Advocates for larger positions, wider stop losses,
    and more aggressive profit targets.
    """

    def __init__(self) -> None:
        self.name = "aggressive_debator"

    async def run(self, state: RiskDebateState) -> RiskDebateState:
        """Generate aggressive risk position."""
        proposed = state.get("proposed_size", 0)
        portfolio = state.get("current_portfolio", {})
        total_equity = portfolio.get("total_equity", 100000)

        # Aggressive: 2% risk per trade
        max_position = total_equity * 0.02
        approved_size = min(proposed, max_position)

        position = RiskPosition(
            debator="aggressive",
            risk_stance="aggressive",
            max_position_pct=2.0,
            stop_loss_pct=3.0,
            take_profit_pct=6.0,
            reasoning=[
                "Strong conviction on this trade",
                "Momentum supports larger position",
                "Upside potential significant",
            ],
            concerns=[
                "Missing opportunity with undersized position",
                "Risk of being stopped out too early",
                "FOMO risk if trade works out",
            ],
            confidence=0.5,
        )

        state["aggressive_position"] = position
        return state


__all__ = [
    "RiskPosition",
    "RiskDebateState",
    "ConservativeDebatorNode",
    "NeutralDebatorNode",
    "AggressiveDebatorNode",
]
