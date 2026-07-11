"""Shared type definitions for Quant Nanggroe AI.

All domain types use Pydantic v2 BaseModel with full validation.
These types form the contract between all modules.
"""

from quant_nanggroe.types.decisions import (
    ConfluenceScore,
    Decision,
    DecisionTable,
    DecisionType,
)
from quant_nanggroe.types.engine import (
    DecisionAction,
    LiquidityLevel,
    MarketRegime,
    MarketState,
    PressureState,
    RiskClearance,
    StrategyStatus,
    VolatilityLevel,
)
from quant_nanggroe.types.market import (
    OHLCV,
    MarketData,
    OrderBook,
    OrderBookLevel,
    Ticker,
    TimeFrame,
)
from quant_nanggroe.types.orders import (
    LimitOrder,
    MarketOrder,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    StopLimitOrder,
    StopOrder,
)
from quant_nanggroe.types.positions import (
    Portfolio,
    Position,
    PositionSide,
)
from quant_nanggroe.types.risk import (
    DrawdownResult,
    PositionSizingResult,
    RiskAssessment,
    RiskLevel,
    VaRResult,
)
from quant_nanggroe.types.signals import (
    Signal,
    SignalStrength,
    SignalType,
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
