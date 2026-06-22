from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    EXIT_ALL = "exit_all"


class SignalStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class Signal(BaseModel):
    id: Optional[str] = None
    symbol: str
    signal_type: SignalType
    confidence: float = Field(..., ge=0.0, le=1.0)
    strength: Optional[SignalStrength] = None
    price: Optional[float] = Field(None, gt=0)
    target_price: Optional[float] = Field(None, gt=0)
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    timeframe: Optional[str] = None
    source_agent: str = ""
    source_strategy: Optional[str] = None
    reasoning: str = ""
    evidence: Dict = Field(default_factory=dict)
    factors: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict = Field(default_factory=dict)

    class Config:
        use_enum_values = False
