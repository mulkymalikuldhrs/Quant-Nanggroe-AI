"""Trading Debate Graph — Full LangGraph debate orchestration.

Combines research debate (Bull/Bear) and risk debate
(Conservative/Neutral/Aggressive) into a single graph with
reflection and final decision synthesis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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

logger = logging.getLogger(__name__)


class DebateResult:
    """Final result from the trading debate."""

    def __init__(
        self,
        symbol: str,
        investment_verdict: str,
        risk_level: str,
        approved_size_pct: float,
        bull_score: float,
        bear_score: float,
        key_factors: List[str],
        conditions: List[str],
    ) -> None:
        self.symbol = symbol
        self.investment_verdict = investment_verdict
        self.risk_level = risk_level
        self.approved_size_pct = approved_size_pct
        self.bull_score = bull_score
        self.bear_score = bear_score
        self.key_factors = key_factors
        self.conditions = conditions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "investment_verdict": self.investment_verdict,
            "risk_level": self.risk_level,
            "approved_size_pct": self.approved_size_pct,
            "bull_score": self.bull_score,
            "bear_score": self.bear_score,
            "key_factors": self.key_factors,
            "conditions": self.conditions,
        }


class TradingDebateGraph:
    """Full trading debate graph combining research and risk debates.

    Orchestrates the full debate flow:
    1. Bull/Bear research debate (configurable rounds)
    2. Risk debate (Conservative/Neutral/Aggressive)
    3. Final decision synthesis

    Usage::

        graph = TradingDebateGraph(max_research_rounds=3)
        result = await graph.run(symbol="AAPL", market_data={...})
    """

    def __init__(
        self,
        max_research_rounds: int = 3,
        llm: Any = None,
    ) -> None:
        self._max_rounds = max_research_rounds
        self._bull = BullResearcherNode(llm=llm)
        self._bear = BearResearcherNode(llm=llm)
        self._conservative = ConservativeDebatorNode()
        self._neutral = NeutralDebatorNode()
        self._aggressive = AggressiveDebatorNode()

    async def run(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        trade_direction: str = "BUY",
        proposed_size: float = 0.0,
        current_portfolio: Optional[Dict[str, Any]] = None,
    ) -> DebateResult:
        """Run the full trading debate.

        Args:
            symbol: Trading symbol.
            market_data: Current market data dict.
            trade_direction: Proposed trade direction.
            proposed_size: Proposed position size.
            current_portfolio: Current portfolio state.

        Returns:
            DebateResult with final decision.
        """
        # Phase 1: Research Debate
        research_state: InvestmentDebateState = {
            "symbol": symbol,
            "market_data": market_data,
            "bull_arguments": [],
            "bear_arguments": [],
            "debate_round": 0,
            "max_rounds": self._max_rounds,
            "bull_score": 0.5,
            "bear_score": 0.5,
            "consensus_reached": False,
            "final_verdict": "",
            "key_factors": [],
        }

        for round_num in range(self._max_rounds):
            research_state = await self._bull.run(research_state)
            research_state = await self._bear.run(research_state)
            research_state["debate_round"] = round_num + 1

            if research_state.get("consensus_reached"):
                break

        if not research_state.get("final_verdict"):
            research_state["final_verdict"] = (
                "BULLISH" if research_state["bull_score"] > research_state["bear_score"]
                else "BEARISH"
            )

        # Extract key factors
        key_factors = []
        for arg in research_state.get("bull_arguments", []):
            key_factors.extend(arg.points[:2])
        for arg in research_state.get("bear_arguments", []):
            key_factors.extend(arg.points[:2])

        # Phase 2: Risk Debate
        risk_state: RiskDebateState = {
            "symbol": symbol,
            "trade_direction": trade_direction,
            "proposed_size": proposed_size,
            "current_portfolio": current_portfolio or {"total_equity": 100000},
            "conservative_position": None,
            "neutral_position": None,
            "aggressive_position": None,
            "debate_round": 0,
            "final_risk_level": "medium",
            "approved_size": 0.0,
            "risk_score": 0.5,
            "conditions": [],
        }

        risk_state = await self._conservative.run(risk_state)
        risk_state = await self._neutral.run(risk_state)
        risk_state = await self._aggressive.run(risk_state)

        # Synthesize risk level (weighted average)
        positions = [
            risk_state.get("conservative_position"),
            risk_state.get("neutral_position"),
            risk_state.get("aggressive_position"),
        ]

        risk_weights = {"conservative": 0.4, "neutral": 0.35, "aggressive": 0.25}
        weighted_size_pct = 0.0
        conditions = []

        for pos in positions:
            if pos:
                weight = risk_weights.get(pos.risk_stance, 0.33)
                weighted_size_pct += pos.max_position_pct * weight
                conditions.extend(pos.concerns[:1])

        # Determine risk level
        if weighted_size_pct <= 0.5:
            risk_level = "low"
        elif weighted_size_pct <= 1.0:
            risk_level = "medium"
        else:
            risk_level = "high"

        return DebateResult(
            symbol=symbol,
            investment_verdict=research_state["final_verdict"],
            risk_level=risk_level,
            approved_size_pct=round(weighted_size_pct, 2),
            bull_score=round(research_state["bull_score"], 3),
            bear_score=round(research_state["bear_score"], 3),
            key_factors=key_factors[:5],
            conditions=conditions[:3],
        )


__all__ = ["DebateResult", "TradingDebateGraph"]
