"""Engine-specific types for Quant Nanggroe AI.

Defines domain types used by the engine layer: market regimes,
pressure states, decision actions, and strategy lifecycle states.
These types form the contract between engine components.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ══════════════════════════════════════════════════════════════════════
# Market Regime & State
# ══════════════════════════════════════════════════════════════════════

class MarketRegime(str, Enum):
    """Market regime classification.

    Deterministic classification based on ADX, RSI, price change, volume, and ATR.
    If regime is NO_TRADE → the entire system must stop.
    """
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    TRENDING = "TRENDING"
    RANGE = "RANGE"
    MEAN_REVERT = "MEAN_REVERT"
    RISK_OFF = "RISK_OFF"
    PANIC = "PANIC"
    NO_TRADE = "NO_TRADE"
    CALM = "CALM"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"


class VolatilityLevel(str, Enum):
    """Market volatility classification."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class LiquidityLevel(str, Enum):
    """Market liquidity classification."""
    THIN = "THIN"
    NORMAL = "NORMAL"
    DEEP = "DEEP"


class MarketState(BaseModel):
    """Current market state summary.

    Combines regime, volatility, and liquidity into a single model
    for use by the decision pipeline.
    """
    regime: MarketRegime = MarketRegime.UNKNOWN
    volatility: VolatilityLevel = VolatilityLevel.NORMAL
    liquidity: LiquidityLevel = LiquidityLevel.NORMAL
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════
# Pressure & Decision
# ══════════════════════════════════════════════════════════════════════

class PressureState(BaseModel):
    """Normalized pressure state from sensor fusion.

    All values are normalized to 0.0-1.0 for deterministic decision synthesis.
    """
    buy_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    sell_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    model_config = {"from_attributes": True}


class RiskClearance(str, Enum):
    """Risk clearance level for trade decisions.

    CLEAR: Trade allowed, all risk checks passed.
    PAUSE: Monitor closely, risk conditions elevated.
    BLOCKED: Trade blocked, risk limits exceeded.
    """
    CLEAR = "CLEAR"
    PAUSE = "PAUSE"
    BLOCKED = "BLOCKED"


class DecisionAction(str, Enum):
    """Action produced by the decision synthesis engine.

    ALLOW_*: Trade approved at the decision layer.
    WATCH_*: Monitoring — do not enter yet.
    NO_TRADE: No action — conditions not met.
    """
    ALLOW_LONG = "ALLOW_LONG"
    ALLOW_SHORT = "ALLOW_SHORT"
    ALLOW_LONG_TRENDING = "ALLOW_LONG_TRENDING"
    ALLOW_SHORT_TRENDING = "ALLOW_SHORT_TRENDING"
    WATCH_LONG = "WATCH_LONG"
    WATCH_SHORT = "WATCH_SHORT"
    NO_TRADE = "NO_TRADE"


# ══════════════════════════════════════════════════════════════════════
# Strategy Lifecycle
# ══════════════════════════════════════════════════════════════════════

class StrategyStatus(str, Enum):
    """Darwinian strategy lifecycle states.

    ACTIVE: Strategy is live and generating trades.
    HIBERNATING: Strategy paused due to excessive drawdown.
    KILLED: Strategy permanently disabled due to negative expectancy.
    """
    ACTIVE = "ACTIVE"
    HIBERNATING = "HIBERNATING"
    KILLED = "KILLED"
