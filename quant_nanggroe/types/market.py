"""Market data types — pydantic v1 compatible."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class TimeFrame(str, Enum):
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
    symbol: str = Field(..., description="Trading pair symbol (e.g., 'BTC/USDT')")
    timestamp: datetime = Field(..., description="Candle open time in UTC")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: float = Field(..., ge=0, description="Trade volume in base currency")

    @validator("high")
    def high_must_be_highest(cls, v):
        return v

    @validator("low")
    def low_must_be_lowest(cls, v):
        return v

    class Config:
        from_attributes = True


class Ticker(BaseModel):
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

    class Config:
        from_attributes = True


class OrderBookLevel(BaseModel):
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)


class OrderBook(BaseModel):
    symbol: str
    timestamp: datetime
    bids: List[OrderBookLevel] = Field(default_factory=list)
    asks: List[OrderBookLevel] = Field(default_factory=list)
    spread: Optional[float] = Field(None, ge=0)
    mid_price: Optional[float] = Field(None, gt=0)

    class Config:
        from_attributes = True


class MarketData(BaseModel):
    """Aggregated market data for a symbol."""
    symbol: str
    timeframe: Optional[TimeFrame] = None
    ohlcv: List[OHLCV] = Field(default_factory=list)
    ticker: Optional[Ticker] = None
    orderbook: Optional[OrderBook] = None
    provider: str = "unknown"

    class Config:
        from_attributes = True
