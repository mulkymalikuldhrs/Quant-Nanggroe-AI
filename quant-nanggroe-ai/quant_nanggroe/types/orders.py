"""Order types — Market, Limit, Stop, and StopLimit orders.

These types define the canonical internal representation of trading orders.
Each order type inherits from a base Order model and adds type-specific fields.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class OrderSide(str, Enum):
    """Order side / direction."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type classification."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(str, Enum):
    """Order lifecycle status."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Order(BaseModel):
    """Base order model with common fields shared by all order types.

    Concrete order types (MarketOrder, LimitOrder, etc.) inherit from this.
    """

    id: str = Field(default_factory=lambda: uuid4().hex, description="Unique order identifier")
    symbol: str = Field(description="Trading pair / ticker symbol")
    side: OrderSide = Field(description="BUY or SELL")
    quantity: float = Field(gt=0, description="Order quantity")
    order_type: OrderType = Field(description="Order type classification")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Current order status")
    created_at: datetime = Field(default_factory=datetime.now, description="Order creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Last status update time")
    filled_quantity: float = Field(default=0.0, ge=0, description="Quantity filled so far")
    filled_price: Optional[float] = Field(default=None, description="Average fill price")
    commission: float = Field(default=0.0, ge=0, description="Commission paid")
    slippage: float = Field(default=0.0, description="Slippage experienced")
    strategy_id: Optional[str] = Field(default=None, description="Strategy that generated this order")
    notes: Optional[str] = Field(default=None, description="Free-form notes")

    model_config = {"json_schema_extra": {
        "examples": [{
            "id": "a1b2c3d4",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.5,
            "order_type": "LIMIT",
            "status": "PENDING",
        }]
    }}


class MarketOrder(Order):
    """Market order — executed immediately at the best available price."""

    order_type: OrderType = OrderType.MARKET

    model_config = {"json_schema_extra": {
        "examples": [{
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.5,
            "order_type": "MARKET",
        }]
    }}


class LimitOrder(Order):
    """Limit order — executed only at the specified price or better."""

    order_type: OrderType = OrderType.LIMIT
    limit_price: float = Field(gt=0, description="Limit price for execution")

    @field_validator("limit_price")
    @classmethod
    def limit_price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("limit_price must be positive")
        return v

    model_config = {"json_schema_extra": {
        "examples": [{
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.5,
            "order_type": "LIMIT",
            "limit_price": 42000.0,
        }]
    }}


class StopOrder(Order):
    """Stop (market) order — triggered when price reaches stop price.

    Once the stop price is reached, a market order is submitted.
    """

    order_type: OrderType = OrderType.STOP
    stop_price: float = Field(gt=0, description="Stop trigger price")

    model_config = {"json_schema_extra": {
        "examples": [{
            "symbol": "BTC/USDT",
            "side": "SELL",
            "quantity": 0.5,
            "order_type": "STOP",
            "stop_price": 40000.0,
        }]
    }}


class StopLimitOrder(Order):
    """Stop-limit order — triggered at stop price, executed at limit price.

    Once the stop price is reached, a limit order is placed at the
    specified limit price.
    """

    order_type: OrderType = OrderType.STOP_LIMIT
    stop_price: float = Field(gt=0, description="Stop trigger price")
    limit_price: float = Field(gt=0, description="Limit price for execution")

    @field_validator("limit_price")
    @classmethod
    def limit_price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("limit_price must be positive")
        return v

    model_config = {"json_schema_extra": {
        "examples": [{
            "symbol": "BTC/USDT",
            "side": "SELL",
            "quantity": 0.5,
            "order_type": "STOP_LIMIT",
            "stop_price": 40000.0,
            "limit_price": 39500.0,
        }]
    }}
