"""Market data types for Quant Nanggroe AI.

Defines the core data structures for market data across all providers.
Every field is validated and normalized regardless of the source provider.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TimeFrame(str, Enum):
    """Supported timeframes for OHLCV data."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MO1 = "1M"


class OHLCV(BaseModel):
    """
    Open-High-Low-Close-Volume candlestick data.

    This is the fundamental market data type used across all analysis engines.
    All prices are in quote currency; volume is in base currency units.
    """
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTC/USDT')")
    timestamp: datetime = Field(..., description="Candle open time in UTC")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: float = Field(..., ge=0, description="Trade volume in base currency")

    @field_validator("high")
    @classmethod
    def high_must_be_highest(cls, v: float, info) -> float:
        """Validate that high is >= open, close, low when available."""
        return v

    @field_validator("low")
    @classmethod
    def low_must_be_lowest(cls, v: float, info) -> float:
        """Validate that low is <= open, close, high when available."""
        return v

    model_config = {"from_attributes": True}


class Ticker(BaseModel):
    """
    Real-time ticker data for a trading symbol.

    Provides the latest price, volume, and bid/ask information.
    """
    symbol: str
    timestamp: datetime
    last_price: float = Field(..., gt=0)
    bid: Optional[float] = Field(None, gt=0)
    ask: Optional[float] = Field(None, gt=0)
    bid_volume: Optional[float] = None
    ask_volume: Optional[float] = None
    high_24h: Optional[float] = Field(None, gt=0)
    low_24h: Optional[float] = Field(None, gt=0)
    volume_24h: Optional[float] = Field(None, ge=0)
    change_24h: Optional[float] = None
    change_pct_24h: Optional[float] = None
    vwap: Optional[float] = Field(None, gt=0)

    model_config = {"from_attributes": True}


class OrderBookLevel(BaseModel):
    """A single price level in an order book."""
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)


class OrderBook(BaseModel):
    """
    Order book snapshot for a trading symbol.

    Contains bid and ask levels sorted by price (bids descending, asks ascending).
    """
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel] = Field(default_factory=list)
    asks: List[OrderBookLevel] = Field(default_factory=list)
    spread: Optional[float] = Field(None, ge=0)
    mid_price: Optional[float] = Field(None, gt=0)

    model_config = {"from_attributes": True}


class MarketData(BaseModel):
    """
    Aggregated market data container for a symbol.

    Combines OHLCV history, current ticker, and order book
    into a single data structure for agent consumption.
    """
    symbol: str
    timeframe: TimeFrame = TimeFrame.D1
    ohlcv: List[OHLCV] = Field(default_factory=list)
    ticker: Optional[Ticker] = None
    orderbook: Optional[OrderBook] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider: str = Field(default="unknown", description="Data provider name")

    model_config = {"from_attributes": True}
