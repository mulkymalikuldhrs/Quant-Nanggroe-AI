"""Decision types for Quant Nanggroe AI.

Defines the decision framework used by the Trading Graph to combine
signals, risk assessments, and portfolio state into final trading decisions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    """Final decision classification."""
    EXECUTE_BUY = "execute_buy"
    EXECUTE_SELL = "execute_sell"
    HOLD_POSITION = "hold_position"
    CLOSE_POSITION = "close_position"
    VETO = "veto"              # Risk engine blocked the trade
    DEFER = "defer"            # Needs more analysis (council debate)
    EMERGENCY_EXIT = "emergency_exit"  # Kill switch activated


class ConfluenceScore(BaseModel):
    """
    Confluence scoring across multiple agents.

    Measures agreement between agents before making a decision.
    Higher confluence = more confidence in the decision.
    """
    total_agents: int = 0
    bullish_agents: int = 0
    bearish_agents: int = 0
    neutral_agents: int = 0
    avg_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    weighted_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    consensus: Optional[str] = None  # "bullish", "bearish", "neutral", "conflicted"

    model_config = {"from_attributes": True}

    def compute_consensus(self) -> str:
        """Determine consensus from agent distribution."""
        if self.total_agents == 0:
            return "no_data"
        bull_pct = self.bullish_agents / self.total_agents
        bear_pct = self.bearish_agents / self.total_agents
        if bull_pct >= 0.6:
            return "bullish"
        elif bear_pct >= 0.6:
            return "bearish"
        elif max(bull_pct, bear_pct) >= 0.4:
            return "conflicted"
        else:
            return "neutral"


class DecisionTable(BaseModel):
    """
    Decision table mapping conditions to actions.

    Based on Quant-Nanggroe-AI's 5-layer deterministic decision pipeline.
    Each entry maps a set of conditions to a trading action.
    """
    id: Optional[str] = None
    name: str
    conditions: Dict[str, str] = Field(
        default_factory=dict,
        description="Condition name → expected value mapping"
    )
    action: DecisionType
    priority: int = Field(default=0, ge=0)
    description: str = ""

    model_config = {"from_attributes": True}


class Decision(BaseModel):
    """
    Final trading decision from the Trading Graph.

    This is the output of the decision pipeline after all agents
    have contributed their analysis and the risk engine has approved.
    """
    id: Optional[str] = None
    symbol: str
    decision_type: DecisionType
    confluence: Optional[ConfluenceScore] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_assessment: Optional[Dict] = None
    signals: List[Dict] = Field(default_factory=list)
    reasoning: str = ""
    order_params: Optional[Dict] = None
    created_at: datetime = Field(default_factory=datetime.now)
    agent_votes: Dict[str, str] = Field(
        default_factory=dict,
        description="Agent name → vote (bullish/bearish/neutral)"
    )
    metadata: Dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}
