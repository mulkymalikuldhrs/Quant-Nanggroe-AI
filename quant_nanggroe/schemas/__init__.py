"""Shared type definitions for Quant Nanggroe AI.

All domain types use Pydantic v2 BaseModel with full validation.
These types form the contract between all modules.
"""

from quant_nanggroe.schemas.market import (
    OHLCV,
    Ticker,
    OrderBook,
    OrderBookLevel,
    MarketData,
    TimeFrame,
)
from quant_nanggroe.schemas.orders import (
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
    LimitOrder,
    MarketOrder,
    StopOrder,
    StopLimitOrder,
)
from quant_nanggroe.schemas.positions import (
    Position,
    PositionSide,
    Portfolio,
)
from quant_nanggroe.schemas.signals import (
    Signal,
    SignalType,
    SignalStrength,
)
from quant_nanggroe.schemas.risk import (
    RiskAssessment,
    RiskLevel,
    VaRResult,
    DrawdownResult,
    PositionSizingResult,
)
from quant_nanggroe.schemas.decisions import (
    Decision,
    DecisionType,
    DecisionTable,
    ConfluenceScore,
)
from quant_nanggroe.schemas.engine import (
    MarketRegime,
    VolatilityLevel,
    LiquidityLevel,
    MarketState,
    PressureState,
    RiskClearance,
    DecisionAction,
    StrategyStatus,
)

__all__ = [
    # Market
    "OHLCV", "Ticker", "OrderBook", "OrderBookLevel", "MarketData", "TimeFrame",
    # Orders
    "Order", "OrderType", "OrderSide", "OrderStatus", "LimitOrder", "MarketOrder",
    "StopOrder", "StopLimitOrder",
    # Positions
    "Position", "PositionSide", "Portfolio",
    # Signals
    "Signal", "SignalType", "SignalStrength",
    # Risk
    "RiskAssessment", "RiskLevel", "VaRResult", "DrawdownResult", "PositionSizingResult",
    # Decisions
    "Decision", "DecisionType", "DecisionTable", "ConfluenceScore",
    # Engine
    "MarketRegime", "VolatilityLevel", "LiquidityLevel", "MarketState",
    "PressureState", "RiskClearance", "DecisionAction", "StrategyStatus",
]
