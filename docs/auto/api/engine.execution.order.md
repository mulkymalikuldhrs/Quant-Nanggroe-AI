# engine.execution.order

## Class: 

Order lifecycle manager.

Tracks all orders, manages state transitions, and provides
query capabilities for order analysis and reconciliation.

**Methods:** __init__, create_order, track, get, update_status, get_by_symbol, get_by_status, get_open_orders, total_orders

*Line: 16*

---

## Function: 

*Line: 23*

---

## Function: 

Create a new order.

Args:
    symbol: Trading symbol.
    side: BUY or SELL.
    quantity: Number of units.
    order_type: Market, limit, stop, etc.
    price: Limit price.
    stop_price: Stop trigger price.
    time_in_force: GTC, DAY, IOC, FOK.

Returns:
    New Order instance with assigned ID.

*Line: 26*

---

## Function: 

Track an existing order.

Args:
    order: Order to track.

*Line: 64*

---

## Function: 

Get an order by ID.

Args:
    order_id: Order ID.

Returns:
    Order if found, None otherwise.

*Line: 72*

---

## Function: 

Update order status.

Args:
    order_id: Order ID.
    status: New status.

Returns:
    Updated Order if found, None otherwise.

*Line: 83*

---

## Function: 

Get all orders for a symbol.

Args:
    symbol: Trading symbol.

Returns:
    List of Orders for the symbol.

*Line: 113*

---

## Function: 

Get all orders with a given status.

Args:
    status: Order status to filter by.

Returns:
    List of Orders with the given status.

*Line: 124*

---

## Function: 

Get all open (pending/submitted) orders.

Returns:
    List of open Orders.

*Line: 135*

---

## Function: 

Total number of tracked orders.

*Line: 147*

---

