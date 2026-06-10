"""Signal types — BUY/SELL/HOLD with confidence and confluence.

Signals are the output of trading agents and strategies. They carry
a directional bias, a confidence score, and provenance metadata.
The ConsensusReport aggregates multiple signals into a final verdict.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SignalAction(str, Enum):
    """Signal directional action."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WAIT = "WAIT"


class Signal(BaseModel):
    """A single trading signal from an agent or strategy.

    Signals carry a directional action, a confidence score (0–1),
    and metadata about the source and reasoning.
    """

    id: str = Field(description="Unique signal identifier")
    symbol: str = Field(description="Trading pair / ticker symbol")
    action: SignalAction = Field(description="BUY / SELL / HOLD / WAIT")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0–1.0")
    source: str = Field(description="Agent or strategy that produced this signal")
    reason: str = Field(default="", description="Human-readable reason for the signal")
    timestamp: datetime = Field(default_factory=datetime.now, description="Signal generation time")
    timeframe: str = Field(default="1d", description="Timeframe the signal applies to")
    entry_price: Optional[float] = Field(default=None, description="Suggested entry price")
    stop_loss: Optional[float] = Field(default=None, description="Suggested stop-loss")
    take_profit: Optional[float] = Field(default=None, description="Suggested take-profit")
    risk_reward_ratio: Optional[float] = Field(default=None, description="Risk/reward ratio")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Signal weight in confluence")

    model_config = {"json_schema_extra": {
        "examples": [{
            "id": "sig_001",
            "symbol": "BTC/USDT",
            "action": "BUY",
            "confidence": 0.85,
            "source": "quant_scanner",
            "reason": "RSI oversold + bullish MACD crossover",
            "entry_price": 42500.0,
            "stop_loss": 41000.0,
            "take_profit": 45000.0,
            "risk_reward_ratio": 1.67,
        }]
    }}


class StrategySignal(BaseModel):
    """A signal from a specific named strategy with category classification.

    Mirrors Quant-Nanggroe-AI's StrategySignal type used by the
    consensus / decision synthesis engine.
    """

    name: str = Field(description="Strategy name")
    category: str = Field(description="Category: SMC, STRUCTURE, RETAIL, etc.")
    action: SignalAction = Field(description="Signal direction")
    strength: float = Field(ge=0.0, le=1.0, description="Signal strength 0.0–1.0")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Weight in consensus")
    description: str = Field(default="", description="Human-readable description")

    model_config = {"json_schema_extra": {
        "examples": [{
            "name": "RSI Divergence",
            "category": "STRUCTURE",
            "action": "BUY",
            "strength": 0.75,
            "weight": 0.25,
            "description": "Bullish RSI divergence on 4H chart",
        }]
    }}


class ConsensusReport(BaseModel):
    """Aggregated consensus from multiple signals / strategies.

    Produces a final verdict with a score, directional counts,
    and the top contributing factors.
    """

    score: float = Field(ge=-1.0, le=1.0, description="Consensus score -1.0 to 1.0")
    verdict: str = Field(description="STRONG BUY / BUY / NEUTRAL / SELL / STRONG SELL")
    total_signals: int = Field(ge=0, description="Total number of signals considered")
    bullish_count: int = Field(ge=0, description="Number of bullish signals")
    bearish_count: int = Field(ge=0, description="Number of bearish signals")
    top_factors: list[str] = Field(default_factory=list, description="Top contributing factors")
    signals: list[StrategySignal] = Field(default_factory=list, description="Individual signals")
    timestamp: datetime = Field(default_factory=datetime.now, description="Report time")

    model_config = {"json_schema_extra": {
        "examples": [{
            "score": 0.65,
            "verdict": "BUY",
            "total_signals": 5,
            "bullish_count": 4,
            "bearish_count": 1,
            "top_factors": ["RSI oversold", "MACD bullish crossover", "VWAP support"],
        }]
    }}
