"""Signal types for Quant Nanggroe AI.

Trading signals are the primary output of analyst and strategist agents.
Each signal carries type, confidence, and supporting evidence.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    """Trading signal direction."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    EXIT_ALL = "exit_all"


class SignalStrength(str, Enum):
    """Signal confidence/strength classification."""
    WEAK = "weak"          # confidence < 0.3
    MODERATE = "moderate"   # 0.3 <= confidence < 0.6
    STRONG = "strong"       # 0.6 <= confidence < 0.8
    VERY_STRONG = "very_strong"  # confidence >= 0.8


class Signal(BaseModel):
    """
    A trading signal produced by an agent.

    Signals carry direction, confidence, target price levels,
    and supporting evidence for downstream consumption by the
    risk and execution agents.
    """
    id: Optional[str] = None
    symbol: str = Field(..., min_length=1)
    signal_type: SignalType
    confidence: float = Field(..., ge=0.0, le=1.0, description="Signal confidence 0.0-1.0")
    strength: Optional[SignalStrength] = None
    price: Optional[float] = Field(None, gt=0, description="Current price when signal generated")
    target_price: Optional[float] = Field(None, gt=0, description="Target price for the signal")
    stop_loss: Optional[float] = Field(None, gt=0, description="Suggested stop-loss price")
    take_profit: Optional[float] = Field(None, gt=0, description="Suggested take-profit price")
    timeframe: Optional[str] = None
    source_agent: str = Field(..., description="Agent that produced this signal")
    source_strategy: Optional[str] = None
    reasoning: str = Field(default="", description="Human-readable reasoning")
    evidence: Dict = Field(default_factory=dict, description="Supporting data/evidence")
    factors: List[str] = Field(default_factory=list, description="Contributing factors")
    timestamp: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}

    def compute_strength(self) -> SignalStrength:
        """Classify signal strength based on confidence."""
        if self.confidence >= 0.8:
            return SignalStrength.VERY_STRONG
        elif self.confidence >= 0.6:
            return SignalStrength.STRONG
        elif self.confidence >= 0.3:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
