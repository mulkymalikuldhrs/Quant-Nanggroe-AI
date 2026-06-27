# exchange.order_types

## Class: 

Extended order lifecycle status with full state machine tracking.

*Line: 59*

---

## Class: 

Raised when an invalid state transition is attempted.

**Methods:** __init__

*Line: 120*

---

## Class: 

Record of a single state transition in the order lifecycle.

Attributes:
    from_state: Previous state.
    to_state: New state.
    timestamp: When the transition occurred.
    reason: Why the transition occurred.

*Line: 131*

---

## Function: 

Validate and record a state transition.

Args:
    current: Current order status.
    target: Target order status.
    reason: Reason for the transition.

Returns:
    :class:`TransitionRecord` documenting the transition.

Raises:
    StateTransitionError: If the transition is not valid.

*Line: 149*

---

## Class: 

Trailing stop order that follows price movements.

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

**Methods:** validate_trail_params, model_post_init, update_price, submit, cancel, reject, is_active, is_triggered, _transition

*Line: 187*

---

## Class: 

Status of a single leg within a bracket order.

*Line: 316*

---

## Class: 

Bracket order — entry + take-profit + stop-loss as atomic unit.

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

**Methods:** validate_prices, model_post_init, submit, fill_entry, fill_take_profit, fill_stop_loss, cancel, is_active, risk_reward_ratio, _transition

*Line: 327*

---

## Class: 

One-Cancels-Other order pair.

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

**Methods:** model_post_init, submit, fill_a, fill_b, cancel, is_active, _transition

*Line: 482*

---

## Class: 

Iceberg order — hidden quantity display for large orders.

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

**Methods:** validate_display_quantity, model_post_init, hidden_quantity, remaining_quantity, submit, fill_portion, cancel, is_active, fill_progress, _transition

*Line: 579*

---

## Function: 

*Line: 123*

---

## Function: 

Ensure at least one trail parameter is set on creation.

*Line: 222*

---

## Function: 

Validate that at least one trail parameter is provided.

*Line: 226*

---

## Function: 

Update the trailing stop based on current market price.

For SELL orders: stop trails UP (peak is highest price seen).
For BUY orders: stop trails DOWN (peak is lowest price seen).

Args:
    current_price: Current market price.

Returns:
    True if the stop price was updated (moved favorably).

*Line: 231*

---

## Function: 

Submit the order.

*Line: 281*

---

## Function: 

Cancel the order.

*Line: 285*

---

## Function: 

Reject the order.

*Line: 289*

---

## Function: 

Whether the order is still active (not in a terminal state).

*Line: 294*

---

## Function: 

Whether the trailing stop has been triggered.

*Line: 299*

---

## Function: 

Perform a state transition with validation.

*Line: 303*

---

## Function: 

Ensure prices are positive.

*Line: 368*

---

## Function: 

Validate price relationships.

*Line: 374*

---

## Function: 

Submit the entry leg of the bracket.

*Line: 404*

---

## Function: 

Mark the entry leg as filled, activating TP and SL legs.

*Line: 409*

---

## Function: 

Mark the take-profit leg as filled, cancel stop-loss.

*Line: 421*

---

## Function: 

Mark the stop-loss leg as filled, cancel take-profit.

*Line: 432*

---

## Function: 

Cancel the bracket order.

*Line: 443*

---

## Function: 

Whether the bracket order is still active.

*Line: 454*

---

## Function: 

Calculate the risk:reward ratio.

*Line: 459*

---

## Function: 

Perform a state transition with validation.

*Line: 469*

---

## Function: 

Validate that order B has either a price or stop price.

*Line: 520*

---

## Function: 

Submit both legs of the OCO order.

*Line: 527*

---

## Function: 

Mark order A as filled, cancel order B.

*Line: 533*

---

## Function: 

Mark order B as filled, cancel order A.

*Line: 544*

---

## Function: 

Cancel both legs of the OCO order.

*Line: 555*

---

## Function: 

Whether the OCO order is still active.

*Line: 562*

---

## Function: 

Perform a state transition with validation.

*Line: 566*

---

## Function: 

Display quantity must be less than total quantity.

*Line: 613*

---

## Function: 

Validate and set initial display quantity.

*Line: 617*

---

## Function: 

Hidden portion of the order remaining.

*Line: 629*

---

## Function: 

Total remaining unfilled quantity.

*Line: 635*

---

## Function: 

Submit the iceberg order.

*Line: 639*

---

## Function: 

Fill a portion of the visible quantity.

When the visible portion is fully filled, replenish from the
hidden portion.

Args:
    fill_qty: Quantity to fill.

Returns:
    The actual quantity filled (may be less if fill exceeds visible).

Raises:
    ValueError: If fill quantity is negative or order is in terminal state.

*Line: 643*

---

## Function: 

Cancel the iceberg order.

*Line: 697*

---

## Function: 

Whether the iceberg order is still active.

*Line: 702*

---

## Function: 

Fill progress as a fraction (0.0 to 1.0).

*Line: 707*

---

## Function: 

Perform a state transition with validation.

*Line: 713*

---

