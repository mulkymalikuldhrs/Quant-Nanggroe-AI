"""Extended Order Types — Advanced order type implementations.

Provides specialized order types beyond the basic market/limit/stop orders,
with full lifecycle tracking via state machines.

Order Types
-----------
- **TrailingStopOrder**: Trailing stop with trail amount or percentage
- **BracketOrder**: Entry + take-profit + stop-loss as atomic unit
- **OCOOrder**: One-cancels-other order pair
- **IcebergOrder**: Hidden quantity display for large orders

State Machine
-------------
All orders track their lifecycle through a state machine with full
transition validation and audit trail.

Usage
-----
.. code-block:: python

    # Trailing stop
    ts = TrailingStopOrder(symbol="BTC/USDT", side=OrderSide.SELL, quantity=1.0,
                           trail_amount=500.0)
    ts.update_price(43000.0)  # Price moves up, stop trails up
    ts.update_price(42500.0)  # Price drops, stop holds

    # Bracket order
    bracket = BracketOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=1.0,
                           entry_price=42000.0, take_profit_price=44000.0,
                           stop_loss_price=41000.0)

    # OCO order
    oco = OCOOrder(symbol="BTC/USDT", side=OrderSide.SELL, quantity=1.0,
                   order_a_price=44000.0, order_b_stop=41000.0)

    # Iceberg order
    iceberg = IcebergOrder(symbol="BTC/USDT", side=OrderSide.BUY, quantity=100.0,
                           display_quantity=10.0)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Order lifecycle state machine
# ---------------------------------------------------------------------------

class ExtendedOrderStatus(str, Enum):
    """Extended order lifecycle status with full state machine tracking."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    TRIGGERED = "triggered"  # Stop/trigger order activated
    ERROR = "error"


# Valid state transitions
_VALID_TRANSITIONS: Dict[ExtendedOrderStatus, set] = {
    ExtendedOrderStatus.PENDING: {
        ExtendedOrderStatus.SUBMITTED,
        ExtendedOrderStatus.CANCELED,
        ExtendedOrderStatus.REJECTED,
        ExtendedOrderStatus.ERROR,
    },
    ExtendedOrderStatus.SUBMITTED: {
        ExtendedOrderStatus.PARTIALLY_FILLED,
        ExtendedOrderStatus.FILLED,
        ExtendedOrderStatus.CANCELED,
        ExtendedOrderStatus.REJECTED,
        ExtendedOrderStatus.EXPIRED,
        ExtendedOrderStatus.TRIGGERED,
        ExtendedOrderStatus.ERROR,
    },
    ExtendedOrderStatus.PARTIALLY_FILLED: {
        ExtendedOrderStatus.PARTIALLY_FILLED,
        ExtendedOrderStatus.FILLED,
        ExtendedOrderStatus.CANCELED,
        ExtendedOrderStatus.ERROR,
    },
    ExtendedOrderStatus.TRIGGERED: {
        ExtendedOrderStatus.PARTIALLY_FILLED,
        ExtendedOrderStatus.FILLED,
        ExtendedOrderStatus.CANCELED,
        ExtendedOrderStatus.REJECTED,
        ExtendedOrderStatus.ERROR,
    },
    # Terminal states — no transitions
    ExtendedOrderStatus.FILLED: set(),
    ExtendedOrderStatus.CANCELED: set(),
    ExtendedOrderStatus.REJECTED: set(),
    ExtendedOrderStatus.EXPIRED: set(),
    ExtendedOrderStatus.ERROR: set(),
}

TERMINAL_STATES = {
    ExtendedOrderStatus.FILLED,
    ExtendedOrderStatus.CANCELED,
    ExtendedOrderStatus.REJECTED,
    ExtendedOrderStatus.EXPIRED,
    ExtendedOrderStatus.ERROR,
}


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: ExtendedOrderStatus, to_state: ExtendedOrderStatus) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid state transition: {from_state.value} → {to_state.value}"
        )


class TransitionRecord(BaseModel):
    """Record of a single state transition in the order lifecycle.

    Attributes:
        from_state: Previous state.
        to_state: New state.
        timestamp: When the transition occurred.
        reason: Why the transition occurred.
    """

    from_state: ExtendedOrderStatus
    to_state: ExtendedOrderStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    reason: str = ""

    class Config:
        from_attributes = True


def transition_status(
    current: ExtendedOrderStatus,
    target: ExtendedOrderStatus,
    reason: str = "",
) -> TransitionRecord:
    """Validate and record a state transition.

    Args:
        current: Current order status.
        target: Target order status.
        reason: Reason for the transition.

    Returns:
        :class:`TransitionRecord` documenting the transition.

    Raises:
        StateTransitionError: If the transition is not valid.
    """
    valid_targets = _VALID_TRANSITIONS.get(current, set())
    if target not in valid_targets:
        raise StateTransitionError(current, target)

    record = TransitionRecord(
        from_state=current,
        to_state=target,
        reason=reason,
    )
    logger.debug(
        "Order state transition: %s → %s (%s)",
        current.value, target.value, reason or "no reason",
    )
    return record


# ---------------------------------------------------------------------------
# Trailing Stop Order
# ---------------------------------------------------------------------------

class TrailingStopOrder(BaseModel):
    """Trailing stop order that follows price movements.

    The stop price trails the market by a fixed amount or percentage.
    When the price moves favorably, the stop follows. When it moves
    unfavorably, the stop holds — locking in gains.

    Attributes:
        id: Unique order identifier.
        symbol: Trading pair (e.g. ``"BTC/USDT"``).
        side: Order direction (BUY or SELL).
        quantity: Order size.
        trail_amount: Fixed trail distance in price units.
        trail_percentage: Trail distance as percentage of peak price.
        status: Current order lifecycle status.
        stop_price: Current calculated stop price.
        peak_price: Highest (for BUY) or lowest (for SELL) price seen.
        created_at: Order creation time.
        transitions: Full audit trail of state transitions.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., pattern="^(buy|sell|BUY|SELL)$")
    quantity: float = Field(..., gt=0)
    trail_amount: Optional[float] = Field(None, gt=0, description="Fixed trail distance in price units")
    trail_percentage: Optional[float] = Field(None, gt=0, le=100, description="Trail distance as %")
    status: ExtendedOrderStatus = ExtendedOrderStatus.PENDING
    stop_price: Optional[float] = None
    peak_price: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    transitions: List[TransitionRecord] = Field(default_factory=list)

    @validator("trail_amount", "trail_percentage")
    def validate_trail_params(cls, v):
        """Ensure at least one trail parameter is set on creation."""
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        """Validate that at least one trail parameter is provided."""
        if self.trail_amount is None and self.trail_percentage is None:
            raise ValueError("Either trail_amount or trail_percentage must be specified")

    def update_price(self, current_price: float) -> bool:
        """Update the trailing stop based on current market price.

        For SELL orders: stop trails UP (peak is highest price seen).
        For BUY orders: stop trails DOWN (peak is lowest price seen).

        Args:
            current_price: Current market price.

        Returns:
            True if the stop price was updated (moved favorably).
        """
        if self.status in TERMINAL_STATES:
            return False

        side_upper = self.side.upper()
        updated = False

        if side_upper == "SELL":
            # For sell trailing stop, peak is highest price
            if self.peak_price is None or current_price > self.peak_price:
                self.peak_price = current_price
                # Calculate new stop price
                if self.trail_amount is not None:
                    self.stop_price = self.peak_price - self.trail_amount
                elif self.trail_percentage is not None:
                    self.stop_price = self.peak_price * (1 - self.trail_percentage / 100)
                updated = True

            # Check if stop is triggered
            if self.stop_price is not None and current_price <= self.stop_price:
                self._transition(ExtendedOrderStatus.TRIGGERED, "Trailing stop triggered")

        elif side_upper == "BUY":
            # For buy trailing stop, peak is lowest price
            if self.peak_price is None or current_price < self.peak_price:
                self.peak_price = current_price
                # Calculate new stop price
                if self.trail_amount is not None:
                    self.stop_price = self.peak_price + self.trail_amount
                elif self.trail_percentage is not None:
                    self.stop_price = self.peak_price * (1 + self.trail_percentage / 100)
                updated = True

            # Check if stop is triggered
            if self.stop_price is not None and current_price >= self.stop_price:
                self._transition(ExtendedOrderStatus.TRIGGERED, "Trailing stop triggered")

        return updated

    def submit(self) -> None:
        """Submit the order."""
        self._transition(ExtendedOrderStatus.SUBMITTED, "Order submitted")

    def cancel(self, reason: str = "Manual cancel") -> None:
        """Cancel the order."""
        self._transition(ExtendedOrderStatus.CANCELED, reason)

    def reject(self, reason: str = "Rejected by exchange") -> None:
        """Reject the order."""
        self._transition(ExtendedOrderStatus.REJECTED, reason)

    @property
    def is_active(self) -> bool:
        """Whether the order is still active (not in a terminal state)."""
        return self.status not in TERMINAL_STATES

    @property
    def is_triggered(self) -> bool:
        """Whether the trailing stop has been triggered."""
        return self.status == ExtendedOrderStatus.TRIGGERED

    def _transition(self, target: ExtendedOrderStatus, reason: str = "") -> None:
        """Perform a state transition with validation."""
        record = transition_status(self.status, target, reason)
        self.transitions.append(record)
        self.status = target

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Bracket Order
# ---------------------------------------------------------------------------

class BracketLegStatus(str, Enum):
    """Status of a single leg within a bracket order."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    TRIGGERED = "triggered"


class BracketOrder(BaseModel):
    """Bracket order — entry + take-profit + stop-loss as atomic unit.

    A bracket order consists of three legs:
    1. **Entry order**: The initial order (market or limit)
    2. **Take-profit order**: Closes position at a profit
    3. **Stop-loss order**: Closes position at a loss

    When the entry is filled, the TP and SL orders are automatically
    submitted. When either TP or SL is filled, the other is canceled.

    Attributes:
        id: Unique order identifier.
        symbol: Trading pair.
        side: Entry direction (BUY or SELL).
        quantity: Order size for all legs.
        entry_price: Entry limit price (None for market entry).
        take_profit_price: Take-profit price.
        stop_loss_price: Stop-loss price.
        status: Overall bracket order status.
        entry_status: Status of the entry leg.
        take_profit_status: Status of the take-profit leg.
        stop_loss_status: Status of the stop-loss leg.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., pattern="^(buy|sell|BUY|SELL)$")
    quantity: float = Field(..., gt=0)
    entry_price: Optional[float] = Field(None, gt=0, description="Entry price (None = market)")
    take_profit_price: float = Field(..., gt=0, description="Take-profit price")
    stop_loss_price: float = Field(..., gt=0, description="Stop-loss price")
    status: ExtendedOrderStatus = ExtendedOrderStatus.PENDING
    entry_status: BracketLegStatus = BracketLegStatus.PENDING
    take_profit_status: BracketLegStatus = BracketLegStatus.PENDING
    stop_loss_status: BracketLegStatus = BracketLegStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    transitions: List[TransitionRecord] = Field(default_factory=list)

    @validator("take_profit_price", "stop_loss_price")
    def validate_prices(cls, v):
        """Ensure prices are positive."""
        if v <= 0:
            raise ValueError("Price must be positive")
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        """Validate price relationships."""
        side_upper = self.side.upper()
        if side_upper == "BUY":
            # For buy: TP > entry > SL
            if self.entry_price:
                if self.take_profit_price <= self.entry_price:
                    raise ValueError(
                        f"BUY bracket: take_profit ({self.take_profit_price}) "
                        f"must be > entry ({self.entry_price})"
                    )
                if self.stop_loss_price >= self.entry_price:
                    raise ValueError(
                        f"BUY bracket: stop_loss ({self.stop_loss_price}) "
                        f"must be < entry ({self.entry_price})"
                    )
        elif side_upper == "SELL":
            # For sell: TP < entry < SL
            if self.entry_price:
                if self.take_profit_price >= self.entry_price:
                    raise ValueError(
                        f"SELL bracket: take_profit ({self.take_profit_price}) "
                        f"must be < entry ({self.entry_price})"
                    )
                if self.stop_loss_price <= self.entry_price:
                    raise ValueError(
                        f"SELL bracket: stop_loss ({self.stop_loss_price}) "
                        f"must be > entry ({self.entry_price})"
                    )

    def submit(self) -> None:
        """Submit the entry leg of the bracket."""
        self._transition(ExtendedOrderStatus.SUBMITTED, "Entry submitted")
        self.entry_status = BracketLegStatus.SUBMITTED

    def fill_entry(self) -> None:
        """Mark the entry leg as filled, activating TP and SL legs."""
        if self.entry_status != BracketLegStatus.SUBMITTED:
            raise StateTransitionError(
                ExtendedOrderStatus.PENDING,
                ExtendedOrderStatus.TRIGGERED,
            )
        self.entry_status = BracketLegStatus.FILLED
        self.take_profit_status = BracketLegStatus.SUBMITTED
        self.stop_loss_status = BracketLegStatus.SUBMITTED
        self._transition(ExtendedOrderStatus.TRIGGERED, "Entry filled, TP/SL activated")

    def fill_take_profit(self) -> None:
        """Mark the take-profit leg as filled, cancel stop-loss."""
        if self.take_profit_status != BracketLegStatus.SUBMITTED:
            raise StateTransitionError(
                ExtendedOrderStatus.TRIGGERED,
                ExtendedOrderStatus.FILLED,
            )
        self.take_profit_status = BracketLegStatus.FILLED
        self.stop_loss_status = BracketLegStatus.CANCELED
        self._transition(ExtendedOrderStatus.FILLED, "Take-profit filled, stop-loss canceled")

    def fill_stop_loss(self) -> None:
        """Mark the stop-loss leg as filled, cancel take-profit."""
        if self.stop_loss_status != BracketLegStatus.SUBMITTED:
            raise StateTransitionError(
                ExtendedOrderStatus.TRIGGERED,
                ExtendedOrderStatus.FILLED,
            )
        self.stop_loss_status = BracketLegStatus.FILLED
        self.take_profit_status = BracketLegStatus.CANCELED
        self._transition(ExtendedOrderStatus.FILLED, "Stop-loss filled, take-profit canceled")

    def cancel(self, reason: str = "Manual cancel") -> None:
        """Cancel the bracket order."""
        if self.entry_status == BracketLegStatus.FILLED:
            # If entry is filled, we need to cancel both TP and SL
            self.take_profit_status = BracketLegStatus.CANCELED
            self.stop_loss_status = BracketLegStatus.CANCELED
        else:
            self.entry_status = BracketLegStatus.CANCELED
        self._transition(ExtendedOrderStatus.CANCELED, reason)

    @property
    def is_active(self) -> bool:
        """Whether the bracket order is still active."""
        return self.status not in TERMINAL_STATES

    @property
    def risk_reward_ratio(self) -> Optional[float]:
        """Calculate the risk:reward ratio."""
        if self.entry_price is None:
            return None
        risk = abs(self.entry_price - self.stop_loss_price)
        reward = abs(self.take_profit_price - self.entry_price)
        if risk == 0:
            return None
        return reward / risk

    def _transition(self, target: ExtendedOrderStatus, reason: str = "") -> None:
        """Perform a state transition with validation."""
        record = transition_status(self.status, target, reason)
        self.transitions.append(record)
        self.status = target

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# OCO Order (One-Cancels-Other)
# ---------------------------------------------------------------------------

class OCOOrder(BaseModel):
    """One-Cancels-Other order pair.

    Two orders are submitted simultaneously. When one is filled,
    the other is automatically canceled.

    Common use cases:
    - Breakout above resistance OR breakdown below support
    - Take profit at target OR stop loss at floor

    Attributes:
        id: Unique order identifier.
        symbol: Trading pair.
        side: Order direction for both legs.
        quantity: Order size for both legs.
        order_a_price: Limit price for order A.
        order_b_price: Limit price for order B.
        order_b_is_stop: If True, order B is a stop order.
        order_b_stop_price: Stop price for order B (if order_b_is_stop).
        status: Overall OCO order status.
        order_a_status: Status of leg A.
        order_b_status: Status of leg B.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., pattern="^(buy|sell|BUY|SELL)$")
    quantity: float = Field(..., gt=0)
    order_a_price: float = Field(..., gt=0, description="Limit price for order A")
    order_b_price: Optional[float] = Field(None, gt=0, description="Limit price for order B")
    order_b_is_stop: bool = False
    order_b_stop_price: Optional[float] = Field(None, gt=0, description="Stop price for order B")
    status: ExtendedOrderStatus = ExtendedOrderStatus.PENDING
    order_a_status: BracketLegStatus = BracketLegStatus.PENDING
    order_b_status: BracketLegStatus = BracketLegStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    transitions: List[TransitionRecord] = Field(default_factory=list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        """Validate that order B has either a price or stop price."""
        if not self.order_b_is_stop and self.order_b_price is None:
            raise ValueError("order_b_price is required when order_b_is_stop is False")
        if self.order_b_is_stop and self.order_b_stop_price is None:
            raise ValueError("order_b_stop_price is required when order_b_is_stop is True")

    def submit(self) -> None:
        """Submit both legs of the OCO order."""
        self._transition(ExtendedOrderStatus.SUBMITTED, "OCO submitted")
        self.order_a_status = BracketLegStatus.SUBMITTED
        self.order_b_status = BracketLegStatus.SUBMITTED

    def fill_a(self) -> None:
        """Mark order A as filled, cancel order B."""
        if self.order_a_status != BracketLegStatus.SUBMITTED:
            raise StateTransitionError(
                ExtendedOrderStatus.SUBMITTED,
                ExtendedOrderStatus.FILLED,
            )
        self.order_a_status = BracketLegStatus.FILLED
        self.order_b_status = BracketLegStatus.CANCELED
        self._transition(ExtendedOrderStatus.FILLED, "Order A filled, Order B canceled")

    def fill_b(self) -> None:
        """Mark order B as filled, cancel order A."""
        if self.order_b_status != BracketLegStatus.SUBMITTED:
            raise StateTransitionError(
                ExtendedOrderStatus.SUBMITTED,
                ExtendedOrderStatus.FILLED,
            )
        self.order_b_status = BracketLegStatus.FILLED
        self.order_a_status = BracketLegStatus.CANCELED
        self._transition(ExtendedOrderStatus.FILLED, "Order B filled, Order A canceled")

    def cancel(self, reason: str = "Manual cancel") -> None:
        """Cancel both legs of the OCO order."""
        self.order_a_status = BracketLegStatus.CANCELED
        self.order_b_status = BracketLegStatus.CANCELED
        self._transition(ExtendedOrderStatus.CANCELED, reason)

    @property
    def is_active(self) -> bool:
        """Whether the OCO order is still active."""
        return self.status not in TERMINAL_STATES

    def _transition(self, target: ExtendedOrderStatus, reason: str = "") -> None:
        """Perform a state transition with validation."""
        record = transition_status(self.status, target, reason)
        self.transitions.append(record)
        self.status = target

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Iceberg Order
# ---------------------------------------------------------------------------

class IcebergOrder(BaseModel):
    """Iceberg order — hidden quantity display for large orders.

    Only a fraction (the "tip") of the total order is visible in the
    order book at any time. As the visible portion is filled, more
    is automatically revealed.

    Attributes:
        id: Unique order identifier.
        symbol: Trading pair.
        side: Order direction.
        total_quantity: Total order size.
        display_quantity: Visible portion in the order book.
        price: Limit price.
        status: Current order lifecycle status.
        filled_quantity: Cumulative filled quantity.
        current_display_quantity: Currently visible quantity.
        hidden_quantity: Hidden portion remaining.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., pattern="^(buy|sell|BUY|SELL)$")
    total_quantity: float = Field(..., gt=0, description="Total order size")
    display_quantity: float = Field(..., gt=0, description="Visible portion in order book")
    price: float = Field(..., gt=0, description="Limit price")
    status: ExtendedOrderStatus = ExtendedOrderStatus.PENDING
    filled_quantity: float = 0.0
    current_display_quantity: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    transitions: List[TransitionRecord] = Field(default_factory=list)

    @validator("display_quantity")
    def validate_display_quantity(cls, v):
        """Display quantity must be less than total quantity."""
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        """Validate and set initial display quantity."""
        if self.display_quantity > self.total_quantity:
            raise ValueError(
                f"display_quantity ({self.display_quantity}) must be <= "
                f"total_quantity ({self.total_quantity})"
            )
        # Set initial visible portion
        if self.current_display_quantity == 0.0:
            self.current_display_quantity = min(self.display_quantity, self.total_quantity)

    @property
    def hidden_quantity(self) -> float:
        """Hidden portion of the order remaining."""
        remaining = self.total_quantity - self.filled_quantity
        return max(0.0, remaining - self.current_display_quantity)

    @property
    def remaining_quantity(self) -> float:
        """Total remaining unfilled quantity."""
        return max(0.0, self.total_quantity - self.filled_quantity)

    def submit(self) -> None:
        """Submit the iceberg order."""
        self._transition(ExtendedOrderStatus.SUBMITTED, "Iceberg order submitted")

    def fill_portion(self, fill_qty: float) -> float:
        """Fill a portion of the visible quantity.

        When the visible portion is fully filled, replenish from the
        hidden portion.

        Args:
            fill_qty: Quantity to fill.

        Returns:
            The actual quantity filled (may be less if fill exceeds visible).

        Raises:
            ValueError: If fill quantity is negative or order is in terminal state.
        """
        if self.status in TERMINAL_STATES:
            raise ValueError(f"Cannot fill order in {self.status.value} state")

        if fill_qty <= 0:
            raise ValueError("Fill quantity must be positive")

        # Cap at visible quantity
        actual_fill = min(fill_qty, self.current_display_quantity)
        self.filled_quantity += actual_fill
        self.current_display_quantity -= actual_fill

        # Replenish visible portion from hidden
        if self.current_display_quantity <= 0 and self.filled_quantity < self.total_quantity:
            remaining = self.total_quantity - self.filled_quantity
            self.current_display_quantity = min(self.display_quantity, remaining)
            self._transition(
                ExtendedOrderStatus.PARTIALLY_FILLED,
                f"Filled {actual_fill}, replenished display",
            )
        elif self.filled_quantity < self.total_quantity:
            if self.status == ExtendedOrderStatus.SUBMITTED:
                self._transition(
                    ExtendedOrderStatus.PARTIALLY_FILLED,
                    f"Partial fill: {actual_fill}",
                )
            else:
                # Already partially filled, just record
                self.transitions.append(TransitionRecord(
                    from_state=self.status,
                    to_state=self.status,
                    reason=f"Additional fill: {actual_fill}",
                ))
        else:
            # Fully filled
            self.current_display_quantity = 0.0
            self._transition(ExtendedOrderStatus.FILLED, "Iceberg fully filled")

        return actual_fill

    def cancel(self, reason: str = "Manual cancel") -> None:
        """Cancel the iceberg order."""
        self._transition(ExtendedOrderStatus.CANCELED, reason)

    @property
    def is_active(self) -> bool:
        """Whether the iceberg order is still active."""
        return self.status not in TERMINAL_STATES

    @property
    def fill_progress(self) -> float:
        """Fill progress as a fraction (0.0 to 1.0)."""
        if self.total_quantity == 0:
            return 0.0
        return self.filled_quantity / self.total_quantity

    def _transition(self, target: ExtendedOrderStatus, reason: str = "") -> None:
        """Perform a state transition with validation."""
        record = transition_status(self.status, target, reason)
        self.transitions.append(record)
        self.status = target

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
