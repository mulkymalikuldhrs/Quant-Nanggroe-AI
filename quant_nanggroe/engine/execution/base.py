"""Abstract Broker Interface and Core Types.

Defines the base interface that all broker implementations must follow,
along with core order and fill types used across the execution engine.

Extracted from OpenAlice's UTA broker layer and Misi-Screener's broker implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderSide(str, Enum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class Order:
    """Order representation.

    Attributes:
        id: Unique order identifier.
        symbol: Trading symbol.
        side: BUY or SELL.
        order_type: Market, limit, stop, etc.
        quantity: Number of units.
        price: Limit price (for limit/stop-limit orders).
        stop_price: Stop trigger price.
        time_in_force: GTC, DAY, IOC, FOK.
        status: Current order status.
        created_at: Order creation timestamp.
        updated_at: Last update timestamp.
        metadata: Additional broker-specific data.
    """

    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    # P0 fix: explicit protective SL/TP so the MT5 adapter can carry them into
    # the broker order (previously naked positions because these were dropped).
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_in_force: str = "GTC"
    status: OrderStatus = OrderStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Fill:
    """Fill (execution) representation.

    Attributes:
        id: Unique fill identifier.
        order_id: Associated order ID.
        symbol: Trading symbol.
        side: BUY or SELL.
        quantity: Filled quantity.
        price: Fill price.
        commission: Commission paid.
        slippage: Slippage from order price.
        timestamp: Fill timestamp.
    """

    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float = 0.0
    slippage: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PositionInfo:
    """Current position information from broker.

    Attributes:
        symbol: Trading symbol.
        quantity: Position size (positive=long, negative=short).
        avg_entry_price: Average entry price.
        current_price: Current market price.
        unrealized_pnl: Unrealized profit/loss.
        market_value: Current market value.
    """

    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    unrealized_pnl: float
    market_value: float


@dataclass
class AccountInfo:
    """Broker account information.

    Attributes:
        balance: Cash balance.
        equity: Total equity (cash + positions).
        margin_used: Margin currently in use.
        margin_available: Available margin.
        buying_power: Total buying power.
    """

    balance: float
    equity: float
    margin_used: float = 0.0
    margin_available: float = 0.0
    buying_power: float = 0.0


class Broker(ABC):
    """Abstract broker interface.

    All broker implementations must inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the broker.

        Returns:
            True if connection successful.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the broker."""
        ...

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Get account information.

        Returns:
            AccountInfo with current account details.
        """
        ...

    @abstractmethod
    async def submit_order(self, order: Order) -> Order:
        """Submit an order to the broker.

        Args:
            order: Order to submit.

        Returns:
            Updated order with broker-assigned ID and status.
        """
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order.

        Args:
            order_id: Order ID to cancel.

        Returns:
            True if cancellation successful.
        """
        ...

    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order status.

        Args:
            order_id: Order ID.

        Returns:
            Order if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_positions(self) -> List[PositionInfo]:
        """Get all open positions.

        Returns:
            List of PositionInfo objects.
        """
        ...

    @abstractmethod
    async def get_price(self, symbol: str) -> float:
        """Get current price for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Current price.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker name identifier."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the broker is currently connected."""
        ...
