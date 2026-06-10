"""Decision types — DecisionTable, Confluence, PressureState, MarketRegime.

These types encode the decision synthesis layer: how market regime,
pressure normalization, and confluence checks combine to produce
a final trading decision. They are the core of the Blueprint Final
specification.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MarketRegime(str, Enum):
    """Market regime classification.

    The regime is the highest-level filter. If the regime is NO_TRADE,
    all agents must remain idle — no exceptions.
    """

    TRENDING = "TRENDING"
    RANGE = "RANGE"
    MEAN_REVERT = "MEAN_REVERT"
    RISK_OFF = "RISK_OFF"
    PANIC = "PANIC"
    NO_TRADE = "NO_TRADE"


class VolatilityLevel(str, Enum):
    """Volatility classification based on ATR percentage."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class LiquidityLevel(str, Enum):
    """Liquidity classification based on volume analysis."""

    THIN = "THIN"
    NORMAL = "NORMAL"
    DEEP = "DEEP"


class PressureState(BaseModel):
    """Normalized pressure state from multiple agent sensors.

    Converts all agent outputs into numerical pressures (0.0–1.0).
    Produced by the PressureNormalizationEngine.

    Inspired by Quant-Nanggroe-AI's PressureState.
    """

    buy_pressure: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized buy pressure 0.0–1.0",
    )
    sell_pressure: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized sell pressure 0.0–1.0",
    )
    volatility_risk: VolatilityLevel = Field(
        default=VolatilityLevel.NORMAL,
        description="Current volatility classification",
    )
    liquidity_condition: LiquidityLevel = Field(
        default=LiquidityLevel.NORMAL,
        description="Current liquidity classification",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confluence confidence score 0.0–1.0",
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def net_pressure(self) -> float:
        """Net directional pressure (positive = bullish)."""
        return self.buy_pressure - self.sell_pressure

    @property
    def total_pressure(self) -> float:
        """Total pressure magnitude."""
        return self.buy_pressure + self.sell_pressure

    model_config = {"json_schema_extra": {
        "examples": [{
            "buy_pressure": 0.72,
            "sell_pressure": 0.28,
            "volatility_risk": "NORMAL",
            "liquidity_condition": "DEEP",
            "confidence_score": 0.72,
        }]
    }}


class ConfluenceStatus(BaseModel):
    """Result of confluence check — is entry allowed?

    The confluence engine checks that multiple conditions align
    before allowing an entry.
    """

    is_allowed: bool = Field(description="Whether entry is permitted")
    score: float = Field(ge=0.0, le=1.0, description="Confluence score 0.0–1.0")
    reason: Optional[str] = Field(default=None, description="Reason if not allowed")

    model_config = {"json_schema_extra": {
        "examples": [
            {"is_allowed": True, "score": 0.82, "reason": None},
            {"is_allowed": False, "score": 0.35, "reason": "Insufficient buy/sell pressure confluence"},
        ]
    }}


class DecisionTableEntry(BaseModel):
    """A single rule in the decision table.

    The decision table maps (regime, pressure, volatility, confidence)
    combinations to actions (ALLOW_ENTRY or NO_TRADE).
    """

    regimes: list[MarketRegime] = Field(description="Applicable market regimes")
    min_buy_pressure: float = Field(ge=0.0, le=1.0, description="Minimum buy pressure")
    max_sell_pressure: float = Field(ge=0.0, le=1.0, description="Maximum sell pressure")
    allowed_volatility: list[VolatilityLevel] = Field(
        description="Permitted volatility levels",
    )
    min_confidence: float = Field(ge=0.0, le=1.0, description="Minimum confidence score")
    action: str = Field(description="ALLOW_ENTRY or NO_TRADE")

    model_config = {"json_schema_extra": {
        "examples": [{
            "regimes": ["TRENDING", "MEAN_REVERT"],
            "min_buy_pressure": 0.6,
            "max_sell_pressure": 0.3,
            "allowed_volatility": ["LOW", "NORMAL"],
            "min_confidence": 0.7,
            "action": "ALLOW_ENTRY",
        }]
    }}


class EntryParameters(BaseModel):
    """Entry parameters produced by the decision synthesis."""

    location: str = Field(description="Entry location description")
    trigger: str = Field(description="Entry trigger type")
    execution: str = Field(description="LIMIT or MARKET")
    entry: float = Field(gt=0, description="Entry price")
    stop_loss: float = Field(gt=0, description="Stop-loss price")
    take_profit: list[float] = Field(description="Take-profit levels")


class DecisionSynthesis(BaseModel):
    """Final synthesized trading decision.

    Combines regime, pressures, confluence, and risk clearance
    into a single actionable decision.
    """

    regime: MarketRegime = Field(description="Current market regime")
    pressures: PressureState = Field(description="Normalized pressure state")
    confluence: ConfluenceStatus = Field(description="Confluence check result")
    entry_parameters: Optional[EntryParameters] = Field(
        default=None,
        description="Entry parameters (only if entry is allowed)",
    )
    risk_clearance: str = Field(description="CLEAR or BLOCKED")
    action: str = Field(description="BUY / SELL / HOLD / WAIT")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"json_schema_extra": {
        "examples": [{
            "regime": "TRENDING",
            "pressures": {
                "buy_pressure": 0.72,
                "sell_pressure": 0.28,
                "volatility_risk": "NORMAL",
                "liquidity_condition": "DEEP",
                "confidence_score": 0.72,
            },
            "confluence": {"is_allowed": True, "score": 0.82},
            "risk_clearance": "CLEAR",
            "action": "BUY",
        }]
    }}
