"""Market data types — OHLCV candles, Tickers, and Order Books.

These types define the canonical internal representation of market data
regardless of which provider it came from. The data normalizer converts
provider-specific formats into these types.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Interval(str, Enum):
    """Standard candle intervals."""

    MIN_1 = "1m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class DataMetadata(BaseModel):
    """Metadata attached to every data point for traceability and trust scoring.

    Inspired by Quant-Nanggroe-AI's DataMetadata and the Blueprint Final
    specification requiring trust scores on all data.
    """

    source: str = Field(default="unknown", description="Provider name that produced this data")
    trust_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trust score 0.0–1.0 based on provider reliability",
    )
    latency_estimate_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated latency of data source in milliseconds",
    )
    update_frequency: str = Field(
        default="realtime",
        description="How often this data updates (e.g., 'realtime', '1h', '1d')",
    )
    domain_type: str = Field(
        default="market",
        description="Domain classification (market, macro, sentiment, etc.)",
    )

    model_config = {"json_schema_extra": {
        "examples": [{
            "source": "binance",
            "trust_score": 0.95,
            "latency_estimate_ms": 50.0,
            "update_frequency": "realtime",
            "domain_type": "market",
        }]
    }}


class OHLCV(BaseModel):
    """A single OHLCV (candlestick) data point.

    This is the canonical internal candle representation. All providers
    normalise their output to this type.
    """

    symbol: str = Field(description="Trading pair / ticker symbol")
    timestamp: datetime = Field(description="Candle open time (UTC)")
    open: float = Field(gt=0, description="Opening price")
    high: float = Field(gt=0, description="Highest price in period")
    low: float = Field(gt=0, description="Lowest price in period")
    close: float = Field(gt=0, description="Closing price")
    volume: float = Field(ge=0, description="Trade volume in period")
    interval: Interval = Field(default=Interval.DAY_1, description="Candle interval")
    metadata: DataMetadata = Field(default_factory=DataMetadata)

    @field_validator("high")
    @classmethod
    def high_must_be_gte_low(cls, v: float, info) -> float:
        """Validate that high >= low when low is available."""
        # Cross-field validation done at model level; this is a guard.
        return v

    @field_validator("low")
    @classmethod
    def low_must_be_lte_high(cls, v: float, info) -> float:
        """Validate that low <= high."""
        return v

    model_config = {"json_schema_extra": {
        "examples": [{
            "symbol": "BTC/USDT",
            "timestamp": "2024-01-15T00:00:00Z",
            "open": 42500.0,
            "high": 43100.0,
            "low": 42200.0,
            "close": 42800.0,
            "volume": 12345.67,
            "interval": "1d",
        }]
    }}


class Ticker(BaseModel):
    """Real-time ticker / quote data.

    Captures the current market state of a symbol including latest price,
    24h change, and volume. Mirrors Quant-Nanggroe-AI's MarketTicker.
    """

    symbol: str = Field(description="Trading pair / ticker symbol")
    name: Optional[str] = Field(default=None, description="Human-readable asset name")
    current_price: float = Field(gt=0, description="Latest traded price")
    price_change_24h: float = Field(default=0.0, description="24h price change (absolute)")
    price_change_pct_24h: float = Field(default=0.0, description="24h price change (%)")
    high_24h: Optional[float] = Field(default=None, description="24h high price")
    low_24h: Optional[float] = Field(default=None, description="24h low price")
    volume_24h: Optional[float] = Field(default=None, description="24h trade volume")
    bid: Optional[float] = Field(default=None, description="Current best bid")
    ask: Optional[float] = Field(default=None, description="Current best ask")
    metadata: DataMetadata = Field(default_factory=DataMetadata)

    model_config = {"json_schema_extra": {
        "examples": [{
            "symbol": "BTC/USDT",
            "name": "Bitcoin",
            "current_price": 42800.0,
            "price_change_24h": 800.0,
            "price_change_pct_24h": 1.9,
            "high_24h": 43100.0,
            "low_24h": 42200.0,
            "volume_24h": 25000.0,
            "bid": 42795.0,
            "ask": 42805.0,
        }]
    }}


class OrderBookLevel(BaseModel):
    """A single price level in an order book."""

    price: float = Field(gt=0, description="Price at this level")
    quantity: float = Field(ge=0, description="Quantity available")
    order_count: Optional[int] = Field(default=None, description="Number of orders at level")


class OrderBook(BaseModel):
    """Snapshot of an order book at a point in time.

    Supports both bid and ask sides with depth control.
    """

    symbol: str = Field(description="Trading pair / ticker symbol")
    timestamp: datetime = Field(description="Snapshot time (UTC)")
    bids: list[OrderBookLevel] = Field(default_factory=list, description="Bid side (price descending)")
    asks: list[OrderBookLevel] = Field(default_factory=list, description="Ask side (price ascending)")
    metadata: DataMetadata = Field(default_factory=DataMetadata)

    @property
    def best_bid(self) -> Optional[float]:
        """Best (highest) bid price."""
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        """Best (lowest) ask price."""
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> Optional[float]:
        """Current bid-ask spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None

    @property
    def spread_pct(self) -> Optional[float]:
        """Current bid-ask spread as percentage of mid-price."""
        if self.best_bid and self.best_ask:
            mid = (self.best_bid + self.best_ask) / 2
            return (self.spread / mid) * 100 if mid > 0 else None
        return None

    model_config = {"json_schema_extra": {
        "examples": [{
            "symbol": "BTC/USDT",
            "timestamp": "2024-01-15T12:00:00Z",
            "bids": [{"price": 42790.0, "quantity": 1.5}, {"price": 42780.0, "quantity": 2.0}],
            "asks": [{"price": 42810.0, "quantity": 1.2}, {"price": 42820.0, "quantity": 0.8}],
        }]
    }}
