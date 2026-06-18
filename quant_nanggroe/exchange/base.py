"""Abstract Exchange Interface — Unified across all brokers.

Defines the canonical interface that every exchange implementation must
satisfy, along with configuration, state, error hierarchy, and WebSocket
callback types.

This interface extends the existing ``engine.execution.base.Broker`` with
full market-data capabilities, portfolio sync, and real-time streaming,
while remaining compatible with the guard pipeline and execution manager.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import BaseModel, Field

from quant_nanggroe.types.market import OHLCV, Ticker, OrderBook, TimeFrame
from quant_nanggroe.types.orders import Order, OrderSide, OrderType, OrderStatus
from quant_nanggroe.types.positions import Position, PositionSide, Portfolio

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------

class ExchangeError(Exception):
    """Base exception for all exchange-related errors.

    All concrete exchange errors inherit from this class so callers can
    catch broadly or narrowly as needed.
    """

    def __init__(self, message: str, exchange: Optional[str] = None, original: Optional[Exception] = None) -> None:
        self.exchange = exchange
        self.original = original
        super().__init__(message)


class ConnectionError(ExchangeError):
    """Failed to connect, or connection was lost."""


class OrderError(ExchangeError):
    """Order submission, cancellation, or validation failed."""

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        exchange: Optional[str] = None,
        original: Optional[Exception] = None,
    ) -> None:
        self.order_id = order_id
        super().__init__(message, exchange=exchange, original=original)


class RateLimitError(ExchangeError):
    """Exchange rate-limit was hit.

    Carries ``retry_after`` seconds when the exchange provides a hint.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float = 60.0,
        exchange: Optional[str] = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, exchange=exchange)


class AuthenticationError(ExchangeError):
    """API key / secret authentication failed."""


class InsufficientFundsError(ExchangeError):
    """Not enough balance to complete the requested operation."""


class MarketDataError(ExchangeError):
    """Market data request failed or returned invalid data."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class ExchangeConfig(BaseModel):
    """Configuration for an exchange connection.

    Attributes:
        exchange_id: Unique identifier for this connection (e.g. ``"binance"``).
        api_key: Exchange API key.
        api_secret: Exchange API secret.
        passphrase: Optional passphrase (OKX, KuCoin).
        sandbox: Use sandbox/testnet mode.
        rate_limit: Maximum requests per second.
        timeout: HTTP request timeout in seconds.
        retries: Number of retries on transient errors.
        retry_delay: Base delay between retries (exponential backoff).
        options: Exchange-specific CCXT options dict.
    """

    exchange_id: str = Field(..., min_length=1, description="Unique exchange identifier")
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    sandbox: bool = False
    rate_limit: float = Field(default=5.0, gt=0, description="Max requests per second")
    timeout: int = Field(default=30, gt=0, description="HTTP timeout in seconds")
    retries: int = Field(default=3, ge=0, description="Number of retries")
    retry_delay: float = Field(default=1.0, ge=0, description="Base retry delay in seconds")
    options: Dict[str, Any] = Field(default_factory=dict, description="Exchange-specific options")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Exchange state
# ---------------------------------------------------------------------------

class ExchangeState(str, Enum):
    """Lifecycle state of an exchange connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


# ---------------------------------------------------------------------------
# WebSocket callback type
# ---------------------------------------------------------------------------

# Callbacks receive a dict payload.  The key ``"type"`` distinguishes
# tickers, order books, trades, etc.
WebSocketCallback = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class ExchangeInterface(ABC):
    """Abstract exchange interface — unified across all brokers.

    Every exchange implementation **must** implement all abstract methods.
    The interface covers:

    * **Connection lifecycle** — connect, disconnect, health checks
    * **Account** — balance, positions, portfolio sync
    * **Trading** — place / cancel / query orders
    * **Market data** — OHLCV, tickers, order books, trades
    * **Real-time** — WebSocket subscribe / unsubscribe
    * **Position tracking** — local position book with P&L

    Design principles
    -----------------
    * All methods are ``async`` — no blocking calls.
    * Methods return Pydantic models from ``quant_nanggroe.types``.
    * Errors are raised as typed exceptions (see error hierarchy above).
    * Rate limiting and retries are built into implementations, not the caller.
    """

    # ----- Connection lifecycle -----

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the exchange.

        Returns:
            ``True`` if the connection was established successfully.

        Raises:
            ConnectionError: If the connection cannot be established.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the exchange connection and clean up resources."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the exchange is currently connected."""

    @property
    @abstractmethod
    def state(self) -> ExchangeState:
        """Current lifecycle state of the connection."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable exchange identifier (e.g. ``"binance"``)."""

    # ----- Account -----

    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """Retrieve current account balances.

        Returns:
            Mapping of asset symbol → free balance.
            Example: ``{"USDT": 50000.0, "BTC": 0.5}``
        """

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Retrieve all open positions.

        Returns:
            List of :class:`~quant_nanggroe.types.positions.Position` instances.
        """

    @abstractmethod
    async def get_portfolio(self) -> Portfolio:
        """Retrieve a full portfolio snapshot.

        Returns:
            :class:`~quant_nanggroe.types.positions.Portfolio` with positions,
            cash, and aggregate metrics.
        """

    # ----- Trading -----

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """Place a new order on the exchange.

        Args:
            symbol: Trading pair (e.g. ``"BTC/USDT"``).
            side: Buy or sell.
            order_type: Market, limit, stop, etc.
            quantity: Order size in base currency.
            price: Limit price (required for limit/stop-limit).
            stop_price: Stop trigger price (required for stop/stop-limit).
            client_order_id: Optional client-assigned ID for idempotency.
            strategy_name: Strategy that generated this order.
            agent_name: Agent that generated this order.
            notes: Free-form notes.

        Returns:
            The submitted :class:`~quant_nanggroe.types.orders.Order` with
            broker-assigned ID and updated status.

        Raises:
            OrderError: On validation or submission failure.
            InsufficientFundsError: If the account lacks balance.
        """

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel an open order.

        Args:
            order_id: Exchange-assigned order ID.
            symbol: Trading pair (required by some exchanges).

        Returns:
            The cancelled :class:`~quant_nanggroe.types.orders.Order`.

        Raises:
            OrderError: If the order cannot be cancelled.
        """

    @abstractmethod
    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Query the current state of an order.

        Args:
            order_id: Exchange-assigned order ID.
            symbol: Trading pair (required by some exchanges).

        Returns:
            The current :class:`~quant_nanggroe.types.orders.Order` state.

        Raises:
            OrderError: If the order is not found.
        """

    # ----- Market data -----

    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV candlestick data.

        Args:
            symbol: Trading pair.
            timeframe: Candle interval.
            since: Start time for the data window.
            limit: Maximum number of candles.

        Returns:
            List of :class:`~quant_nanggroe.types.market.OHLCV` candles.

        Raises:
            MarketDataError: On data retrieval failure.
        """

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Fetch the latest ticker for a symbol.

        Args:
            symbol: Trading pair.

        Returns:
            :class:`~quant_nanggroe.types.market.Ticker` snapshot.

        Raises:
            MarketDataError: On data retrieval failure.
        """

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Fetch the current order book for a symbol.

        Args:
            symbol: Trading pair.
            limit: Depth per side.

        Returns:
            :class:`~quant_nanggroe.types.market.OrderBook` snapshot.

        Raises:
            MarketDataError: On data retrieval failure.
        """

    @abstractmethod
    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch recent public trades.

        Args:
            symbol: Trading pair.
            since: Only return trades after this time.
            limit: Maximum number of trades.

        Returns:
            List of trade dicts with keys ``id``, ``price``, ``amount``,
            ``side``, ``timestamp``.

        Raises:
            MarketDataError: On data retrieval failure.
        """

    # ----- WebSocket / real-time -----

    @abstractmethod
    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time ticker updates.

        Args:
            symbol: Trading pair.
            callback: Async callback invoked on each update.
        """

    @abstractmethod
    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time order book updates.

        Args:
            symbol: Trading pair.
            callback: Async callback invoked on each update.
        """

    @abstractmethod
    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time trade updates.

        Args:
            symbol: Trading pair.
            callback: Async callback invoked on each update.
        """

    @abstractmethod
    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Unsubscribe from a real-time data stream.

        Args:
            symbol: Trading pair.
            channel: Stream type (``"ticker"``, ``"orderbook"``, ``"trades"``).
        """

    # ----- Utility -----

    @abstractmethod
    async def get_markets(self) -> List[str]:
        """List all tradable symbols on the exchange.

        Returns:
            List of symbol strings (e.g. ``["BTC/USDT", "ETH/USDT"]``).
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify that the exchange connection is healthy.

        Returns:
            ``True`` if the exchange is responsive.
        """
