# agents.execution.tools

## Function: 

Lazy-load ExecutionManager from engine.

*Line: 35*

---

## Function: 

Lazy-load ExecutionTool from shared tools.

*Line: 49*

---

## Function: 

*Line: 63*

---

## Function: 

*Line: 82*

---

## Function: 

*Line: 94*

---

## Function: 

Submit an order to the broker.

PRODUCTION: Uses ExecutionManager for real order routing through
PaperBroker (or live broker when configured).
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Trading symbol
    action: BUY or SELL
    quantity: Number of shares/contracts
    order_type: Order type (market, limit, stop, stop_limit)
    price: Limit price (required for limit orders)
    time_in_force: Time in force (GTC, DAY, IOC, FOK)

Returns:
    JSON string with order submission result

*Line: 120*

---

## Function: 

Cancel an existing order.

PRODUCTION: Uses ExecutionManager/OrderManager for real cancellation.
Falls back to mock data only in _MOCK_MODE.

Args:
    order_id: Order ID to cancel
    reason: Cancellation reason

Returns:
    JSON string with cancellation result

*Line: 226*

---

## Function: 

Get order fill information.

PRODUCTION: Uses FillTracker for real fill data.
Falls back to mock data only in _MOCK_MODE.

Args:
    order_id: Optional specific order ID (returns all if not specified)

Returns:
    JSON string with fill information

*Line: 291*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 19*

---

## Function: 

*Line: 23*

---

