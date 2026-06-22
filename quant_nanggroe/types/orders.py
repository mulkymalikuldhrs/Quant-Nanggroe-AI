"""Order types — pydantic v1 compatible."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    TAKE_PROFIT = "take_profit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"


class Order(BaseModel):
    id: Optional[str] = None
    client_order_id: Optional[str] = None
    symbol: str = Field(..., min_length=1, description="Trading pair symbol")
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(..., gt=0, description="Order quantity in base currency")
    price: Optional[float] = Field(None, gt=0, description="Limit price")
    stop_price: Optional[float] = Field(None, gt=0, description="Stop trigger price")
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = Field(default=0.0, ge=0)
    average_fill_price: Optional[float] = Field(None, gt=0)
    commission: float = Field(default=0.0, ge=0)
    slippage: float = Field(default=0.0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    broker_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    strategy_name: Optional[str] = None
    agent_name: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class MarketOrder(Order):
    order_type: OrderType = OrderType.MARKET


class LimitOrder(Order):
    order_type: OrderType = OrderType.LIMIT
    price: float = Field(..., gt=0, description="Limit price (required)")


class StopOrder(Order):
    order_type: OrderType = OrderType.STOP
    stop_price: float = Field(..., gt=0, description="Stop trigger price (required)")


class StopLimitOrder(Order):
    order_type: OrderType = OrderType.STOP_LIMIT
    price: float = Field(..., gt=0, description="Limit price (required)")
    stop_price: float = Field(..., gt=0, description="Stop trigger price (required)")
