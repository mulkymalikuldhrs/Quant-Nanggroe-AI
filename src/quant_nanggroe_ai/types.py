"""
Shared Types — From Quant-Nanggroe-AI types.ts
===============================================
Pydantic models mirroring the TypeScript type definitions,
with Python-native enhancements for the engine layer.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ══════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════


class MarketRegime(str, Enum):
    """Market regime classification."""

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
    """Volatility classification."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class LiquidityLevel(str, Enum):
    """Liquidity classification."""

    THIN = "THIN"
    NORMAL = "NORMAL"
    DEEP = "DEEP"


class TradeDirection(str, Enum):
    """Trade direction."""

    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"
    SHORT = "SHORT"


class RiskClearance(str, Enum):
    """Risk clearance status."""

    CLEAR = "CLEAR"
    BLOCKED = "BLOCKED"
    PAUSE = "PAUSE"


class DecisionAction(str, Enum):
    """Decision synthesis action."""

    ALLOW_LONG = "ALLOW_LONG"
    ALLOW_SHORT = "ALLOW_SHORT"
    ALLOW_LONG_TRENDING = "ALLOW_LONG_TRENDING"
    ALLOW_SHORT_TRENDING = "ALLOW_SHORT_TRENDING"
    WATCH_LONG = "WATCH_LONG"
    WATCH_SHORT = "WATCH_SHORT"
    NO_TRADE = "NO_TRADE"


class StrategyStatus(str, Enum):
    """Strategy lifecycle status."""

    ACTIVE = "ACTIVE"
    HIBERNATING = "HIBERNATING"
    KILLED = "KILLED"


class NewsEventType(str, Enum):
    """News event classification."""

    MACRO = "MACRO"
    SCHEDULED = "SCHEDULED"
    SHOCK = "SHOCK"
    NOISE = "NOISE"


class AgentCapability(str, Enum):
    """Agent capability classification."""

    PORTFOLIO_MANAGER = "portfolio-manager"
    QUANT = "quant"
    FUNDAMENTAL = "fundamental"
    RISK_MANAGER = "risk-manager"
    ALGO_DEV = "algo-dev"
    GENERAL = "general"


# ══════════════════════════════════════════════════════════════════════
# MARKET DATA TYPES
# ══════════════════════════════════════════════════════════════════════


class CandleData(BaseModel):
    """OHLCV candle data."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class DataMetadata(BaseModel):
    """Metadata about a data source."""

    source: str
    trust_score: float = Field(ge=0.0, le=1.0)
    latency_estimate_ms: int = 0
    update_frequency: str = "realtime"
    domain_type: str = "market"


# ══════════════════════════════════════════════════════════════════════
# ENGINE TYPES
# ══════════════════════════════════════════════════════════════════════


class TradingConstitution(BaseModel):
    """Constitutional trading rules — the law of the system."""

    risk_greater_than_opportunity: bool = True
    regime_greater_than_strategy: bool = True
    structure_greater_than_indicator: bool = True
    invalidation_greater_than_rr: bool = True
    no_trade_is_valid_decision: bool = True
    max_leverage: int = 1
    max_correlation: float = 0.7
    max_exposure_per_asset: float = 0.1
    daily_drawdown_limit: float = 0.01


class PressureState(BaseModel):
    """Normalized buy/sell pressure state."""

    buy_pressure: float = Field(ge=0.0, le=1.0, default=0.0)
    sell_pressure: float = Field(ge=0.0, le=1.0, default=0.0)
    volatility_risk: VolatilityLevel = VolatilityLevel.NORMAL
    liquidity_condition: LiquidityLevel = LiquidityLevel.NORMAL
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)


class MarketState(BaseModel):
    """Current market state classification."""

    regime: MarketRegime = MarketRegime.UNKNOWN
    volatility: VolatilityLevel = VolatilityLevel.NORMAL
    liquidity: LiquidityLevel = LiquidityLevel.NORMAL
    timestamp: datetime = Field(default_factory=datetime.now)


class RiskCheckpointResult(BaseModel):
    """Individual risk checkpoint result."""

    name: str
    value: str
    limit: str
    passed: bool


class RiskVerdict(BaseModel):
    """Full risk verdict from the 9-checkpoint system."""

    symbol: str
    direction: str
    verdict: str  # "APPROVED" or "VETOED"
    risk_pct: float
    checkpoints: dict[str, RiskCheckpointResult]
    veto_count_total: int = 0
    approval_count_total: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class DecisionSynthesis(BaseModel):
    """Final decision synthesis output."""

    regime: MarketRegime
    pressures: PressureState
    risk_clearance: RiskClearance = RiskClearance.BLOCKED
    action: DecisionAction = DecisionAction.NO_TRADE
    reason: str = ""
    confidence: float = 0.0
    matched_rules: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class EntryParameters(BaseModel):
    """Entry parameters for a trade."""

    location: str  # DISCOUNT_ZONE / PREMIUM_ZONE
    trigger: str
    execution: str  # LIMIT / MARKET
    entry: float
    sl: float
    tp: list[float]


# ══════════════════════════════════════════════════════════════════════
# AGENT TYPES
# ══════════════════════════════════════════════════════════════════════


class QuantScannerOutput(BaseModel):
    """Quant scanner sensor output."""

    trend_strength: float = Field(ge=0.0, le=1.0, default=0.5)
    structure_state: str = "NEUTRAL"  # BULL / BEAR / NEUTRAL
    volatility_expansion: bool = False


class SMCOutput(BaseModel):
    """Smart Money Concepts sensor output."""

    liquidity_sweep: bool = False
    displacement_strength: float = Field(ge=0.0, le=1.0, default=0.0)
    poi_validity: float = Field(ge=0.0, le=1.0, default=0.0)


class NewsSentinelOutput(BaseModel):
    """News sentinel sensor output."""

    event_type: NewsEventType = NewsEventType.NOISE
    impact_score: float = Field(ge=0.0, le=1.0, default=0.0)
    directional_uncertainty: float = Field(ge=0.0, le=1.0, default=0.5)
    time_decay: int = 0  # seconds


class FlowWhaleOutput(BaseModel):
    """Flow/whale sensor output."""

    positioning_bias: str = "NEUTRAL"  # LONG / SHORT / NEUTRAL
    flow_imbalance: float = Field(ge=0.0, le=1.0, default=0.0)


class StrategyLifecycle(BaseModel):
    """Strategy lifecycle tracking."""

    id: str
    name: str
    status: StrategyStatus = StrategyStatus.ACTIVE
    expectancy: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    sample_size: int = 0
    trades_count: int = 0
    death_threshold: int = 20


# ══════════════════════════════════════════════════════════════════════
# PORTFOLIO TYPES
# ══════════════════════════════════════════════════════════════════════


class PortfolioPosition(BaseModel):
    """Portfolio position."""

    ticker: str
    amount: float
    avg_price: float
    current_price: float
    pnl: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.now)


class TradeHistoryItem(BaseModel):
    """Trade history record."""

    id: str
    timestamp: datetime
    ticker: str
    action: TradeDirection
    amount: float
    price: float
    total_value: float
    fees: float = 0.0
    realized_pnl: float | None = None
    triggered_by_signals: list[str] = Field(default_factory=list)
