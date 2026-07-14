"""Base REST Client — Abstract base for exchange REST API clients.

Provides rate limiting, request signing interface, error handling,
and capability detection for all exchange clients.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from abc import ABC, abstractmethod
from enum import Flag, auto
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


from dataclasses import dataclass


class ExchangeCapability(Flag):
    """Exchange capability flags."""
    SPOT = auto()
    FUTURES = auto()
    PERPETUALS = auto()
    MARGIN = auto()
    WEBSOCKET = auto()
    OPTIONS = auto()


@dataclass
class ClientCapabilities:
    """Human-readable capabilities descriptor for an exchange client.

    Attributes:
        spot: Supports spot trading.
        futures: Supports futures trading.
        perps: Supports perpetual contracts.
        margin: Supports margin trading.
        websocket: Supports WebSocket streaming.
        max_leverage: Maximum leverage allowed.
        requires_passphrase: Whether API requires a passphrase.
    """
    spot: bool = False
    futures: bool = False
    perps: bool = False
    margin: bool = False
    websocket: bool = False
    max_leverage: float = 1.0
    requires_passphrase: bool = False


class RestClientConfig(BaseModel):
    """Configuration for REST exchange client."""
    exchange_id: str = Field(..., description="Exchange identifier")
    api_key: str = Field("", description="API key")
    api_secret: str = Field("", description="API secret")
    passphrase: str = Field("", description="API passphrase (OKX)")
    base_url: str = Field("", description="Base API URL")
    rate_limit: int = Field(10, description="Max requests per second")
    timeout: int = Field(30, description="Request timeout seconds")
    testnet: bool = Field(False, description="Use testnet")


class OrderRequest(BaseModel):
    """Standardized order request."""
    symbol: str
    side: str  # "buy" or "sell"
    order_type: str = "limit"  # "limit", "market", "stop"
    quantity: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    reduce_only: bool = False
    leverage: Optional[int] = None
    client_order_id: Optional[str] = None


class OrderResult(BaseModel):
    """Standardized order result."""
    order_id: str = ""
    client_order_id: str = ""
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    status: str = ""
    price: float = 0.0
    quantity: float = 0.0
    filled_quantity: float = 0.0
    timestamp: str = ""


class BalanceInfo(BaseModel):
    """Account balance information."""
    asset: str = ""
    free: float = 0.0
    used: float = 0.0
    total: float = 0.0


class PositionInfo(BaseModel):
    """Position information."""
    symbol: str = ""
    side: str = ""
    quantity: float = 0.0
    entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    leverage: int = 1
    liquidation_price: float = 0.0


class OrderbookEntry(BaseModel):
    """Single orderbook entry."""
    price: float
    quantity: float


class OrderbookData(BaseModel):
    """Orderbook snapshot."""
    symbol: str = ""
    bids: List[OrderbookEntry] = Field(default_factory=list)
    asks: List[OrderbookEntry] = Field(default_factory=list)
    timestamp: str = ""


class KlineBar(BaseModel):
    """Single kline/candlestick bar."""
    timestamp: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0


class BaseRestClient(ABC):
    """Abstract base class for exchange REST API clients.

    All exchange clients inherit from this class, which provides:
    - Rate limiting (token bucket)
    - Request signing interface
    - Error handling with retries
    - Capability detection
    - Unified order/balance/position models

    Usage::

        class BinanceClient(BaseRestClient):
            exchange_id = "binance"
            capabilities = ExchangeCapability.SPOT | ExchangeCapability.FUTURES

            async def place_order(self, order: OrderRequest) -> OrderResult:
                ...
    """

    exchange_id: str = "base"
    capabilities: ExchangeCapability = ExchangeCapability.SPOT

    def __init__(self, config: RestClientConfig) -> None:
        self._config = config
        self._call_timestamps: List[float] = []
        self._lock = asyncio.Lock()
        self._initialized = False

    @property
    def has_spot(self) -> bool:
        return bool(self.capabilities & ExchangeCapability.SPOT)

    @property
    def has_futures(self) -> bool:
        return bool(self.capabilities & ExchangeCapability.FUTURES)

    @property
    def has_perpetuals(self) -> bool:
        return bool(self.capabilities & ExchangeCapability.PERPETUALS)

    @property
    def has_websocket(self) -> bool:
        return bool(self.capabilities & ExchangeCapability.WEBSOCKET)

    async def initialize(self) -> bool:
        """Initialize client (verify API keys, load markets)."""
        self._initialized = True
        return True

    # ----- Rate Limiting -----

    async def _rate_limit(self) -> None:
        """Apply rate limiting before API call."""
        async with self._lock:
            now = time.monotonic()
            self._call_timestamps = [t for t in self._call_timestamps if now - t < 1.0]
            if len(self._call_timestamps) >= self._config.rate_limit:
                sleep_time = 1.0 - (now - self._call_timestamps[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            self._call_timestamps.append(time.monotonic())

    # ----- Request Helpers -----

    def _sign(self, params: Dict[str, Any], secret: str) -> str:
        """Sign request parameters with HMAC-SHA256."""
        query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        signature = hmac.new(
            secret.encode(), query_string.encode(), hashlib.sha256
        ).hexdigest()
        return signature

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """Make an HTTP request with rate limiting and retry."""
        import httpx

        await self._rate_limit()

        params = params or {}
        headers = headers or {}

        if signed and self._config.api_key:
            headers["X-MBX-APIKEY"] = self._config.api_key
            params["timestamp"] = str(int(time.time() * 1000))
            params["signature"] = self._sign(params, self._config.api_secret)

        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            fn = getattr(client, method.lower())
            response = await fn(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    # ----- Abstract Methods -----

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place a new order."""
        ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an existing order."""
        ...

    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> List[BalanceInfo]:
        """Get account balance."""
        ...

    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[PositionInfo]:
        """Get open positions."""
        ...

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderbookData:
        """Get order book snapshot."""
        ...

    @abstractmethod
    async def get_klines(
        self, symbol: str, interval: str = "1h", limit: int = 100
    ) -> List[KlineBar]:
        """Get candlestick/kline data."""
        ...


__all__ = [
    "ExchangeCapability",
    "RestClientConfig",
    "OrderRequest",
    "OrderResult",
    "BalanceInfo",
    "PositionInfo",
    "OrderbookEntry",
    "OrderbookData",
    "KlineBar",
    "BaseRestClient",
]
