"""Market data types for Quant-Nanggroe-AI."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TimeFrame(str, Enum):
    """Supported timeframes for market data."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MO1 = "1mo"


class OHLCV(BaseModel):
    """OHLCV bar data."""
    symbol: str
    timestamp: datetime
    timeframe: TimeFrame = TimeFrame.D1
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None
    trade_count: Optional[int] = None
    source: str = "unknown"

    model_config = {"frozen": True}


class Ticker(BaseModel):
    """Real-time ticker data."""
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    volume: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "unknown"


class OrderBookLevel(BaseModel):
    """Single level of an order book."""
    price: float
    size: float


class OrderBook(BaseModel):
    """Order book snapshot."""
    symbol: str
    bids: list[OrderBookLevel] = Field(default_factory=list)
    asks: list[OrderBookLevel] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "unknown"


class MarketData(BaseModel):
    """Unified market data container."""
    symbol: str
    ohlcv: Optional[OHLCV] = None
    ticker: Optional[Ticker] = None
    order_book: Optional[OrderBook] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "unknown"
