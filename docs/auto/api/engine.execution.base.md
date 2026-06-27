# engine.execution.base

## Class: 

Order side.

*Line: 20*

---

## Class: 

Order type.

*Line: 27*

---

## Class: 

Order status.

*Line: 37*

---

## Class: 

Order representation.

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

*Line: 50*

---

## Class: 

Fill (execution) representation.

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

*Line: 83*

---

## Class: 

Current position information from broker.

Attributes:
    symbol: Trading symbol.
    quantity: Position size (positive=long, negative=short).
    avg_entry_price: Average entry price.
    current_price: Current market price.
    unrealized_pnl: Unrealized profit/loss.
    market_value: Current market value.

*Line: 110*

---

## Class: 

Broker account information.

Attributes:
    balance: Cash balance.
    equity: Total equity (cash + positions).
    margin_used: Margin currently in use.
    margin_available: Available margin.
    buying_power: Total buying power.

*Line: 131*

---

## Class: 

Abstract broker interface.

All broker implementations must inherit from this class
and implement the required methods.

**Methods:** name, is_connected

*Line: 149*

---

## Function: 

Broker name identifier.

*Line: 238*

---

## Function: 

Whether the broker is currently connected.

*Line: 244*

---

