"""Shared type definitions for Quant Nanggroe AI.

All types are Pydantic BaseModel v2 with full type annotations,
validators where appropriate, and JSON serialization support.
"""

from quant_nanggroe.types.market import OHLCV, Ticker, OrderBook, OrderBookLevel, DataMetadata
from quant_nanggroe.types.orders import (
    OrderSide,
    OrderType,
    OrderStatus,
    Order,
    MarketOrder,
    LimitOrder,
    StopOrder,
    StopLimitOrder,
)
from quant_nanggroe.types.positions import Position, PositionSide, PositionStatus
from quant_nanggroe.types.signals import (
    SignalAction,
    Signal,
    StrategySignal,
    ConsensusReport,
)
from quant_nanggroe.types.risk import (
    RiskMetrics,
    VaRResult,
    DrawdownResult,
    TradingConstitution,
)
from quant_nanggroe.types.agents import (
    AgentState,
    AgentConfig,
    AgentCapability,
    AgentStatus,
    AgentContract,
)
from quant_nanggroe.types.decisions import (
    MarketRegime,
    VolatilityLevel,
    LiquidityLevel,
    PressureState,
    ConfluenceStatus,
    DecisionTableEntry,
    DecisionSynthesis,
)

__all__ = [
    # Market
    "OHLCV", "Ticker", "OrderBook", "OrderBookLevel", "DataMetadata",
    # Orders
    "OrderSide", "OrderType", "OrderStatus", "Order", "MarketOrder",
    "LimitOrder", "StopOrder", "StopLimitOrder",
    # Positions
    "Position", "PositionSide", "PositionStatus",
    # Signals
    "SignalAction", "Signal", "StrategySignal", "ConsensusReport",
    # Risk
    "RiskMetrics", "VaRResult", "DrawdownResult", "TradingConstitution",
    # Agents
    "AgentState", "AgentConfig", "AgentCapability", "AgentStatus", "AgentContract",
    # Decisions
    "MarketRegime", "VolatilityLevel", "LiquidityLevel", "PressureState",
    "ConfluenceStatus", "DecisionTableEntry", "DecisionSynthesis",
]
