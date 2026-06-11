"""Shared type definitions for Quant Nanggroe AI.

All domain types use Pydantic v2 BaseModel with full validation.
These types form the contract between all modules.
"""

from quant_nanggroe.types.market import (
    OHLCV,
    Ticker,
    OrderBook,
    OrderBookLevel,
    MarketData,
    TimeFrame,
)
from quant_nanggroe.types.orders import (
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
    LimitOrder,
    MarketOrder,
    StopOrder,
    StopLimitOrder,
)
from quant_nanggroe.types.positions import (
    Position,
    PositionSide,
    Portfolio,
)
from quant_nanggroe.types.signals import (
    Signal,
    SignalType,
    SignalStrength,
)
from quant_nanggroe.types.risk import (
    RiskAssessment,
    RiskLevel,
    VaRResult,
    DrawdownResult,
    PositionSizingResult,
)
from quant_nanggroe.types.decisions import (
    Decision,
    DecisionType,
    DecisionTable,
    ConfluenceScore,
)

__all__ = [
    "OHLCV", "Ticker", "OrderBook", "OrderBookLevel", "MarketData", "TimeFrame",
    "Order", "OrderType", "OrderSide", "OrderStatus", "LimitOrder", "MarketOrder",
    "StopOrder", "StopLimitOrder",
    "Position", "PositionSide", "Portfolio",
    "Signal", "SignalType", "SignalStrength",
    "RiskAssessment", "RiskLevel", "VaRResult", "DrawdownResult", "PositionSizingResult",
    "Decision", "DecisionType", "DecisionTable", "ConfluenceScore",
]
