# agents.tools.execution

## Function: 

Check if symbol is a crypto asset.

*Line: 55*

---

## Function: 

Check if symbol is a forex pair.

*Line: 63*

---

## Function: 

Normalize order side string to OrderSide enum.

Args:
    side: "BUY", "SELL", "LONG", or "SHORT"

Returns:
    OrderSide enum value.

Raises:
    ExecutionError: If the side string is invalid.

*Line: 68*

---

## Function: 

Normalize order type string to OrderType enum.

*Line: 89*

---

## Class: 

In-memory order store for tracking all orders across brokers.

Provides lookup by order_id for status queries and cancellation.

**Methods:** __init__, store, get, update, list_by_symbol, list_open

*Line: 103*

---

## Class: 

Trade execution tool for agent consumption.

Provides a unified interface for order submission, cancellation,
and status tracking across multiple execution backends.

Features:
  - Automatic routing to the appropriate broker backend
  - Paper trading mode by default (safe for testing)
  - Pre-trade risk checks (kill switch, position limits)
  - Full audit trail in the order store
  - Stop-loss and take-profit order support

Usage::

    tool = ExecutionTool()
    result = await tool.execute_order(
        symbol="AAPL",
        side="BUY",
        quantity=10,
        order_type="LIMIT",
        price=150.0,
    )
    print(result["status"])     # "filled"
    print(result["order_id"])   # UUID

**Methods:** __init__, _validate_order_params, _should_use_alpaca, _get_paper_broker, _get_paper_broker_by_type, _get_alpaca_broker, _build_order_result

*Line: 142*

---

## Function: 

Get or create the default ExecutionTool instance.

*Line: 603*

---

## Function: 

*Line: 110*

---

## Function: 

Store an order record.

*Line: 113*

---

## Function: 

Get an order record by ID.

*Line: 117*

---

## Function: 

Update fields on an existing order record.

*Line: 121*

---

## Function: 

List all orders for a given symbol.

*Line: 126*

---

## Function: 

List all open (non-filled, non-cancelled) orders.

*Line: 133*

---

## Function: 

Initialize the ExecutionTool.

Args:
    market_data_tool: Optional MarketDataTool for fetching
        current prices when executing market orders.

*Line: 170*

---

## Function: 

Validate order parameters before submission.

*Line: 408*

---

## Function: 

Check if Alpaca should be used for stock execution.

*Line: 486*

---

## Function: 

Get the appropriate paper broker for a symbol type.

*Line: 497*

---

## Function: 

Get paper broker by asset type string.

*Line: 505*

---

## Function: 

Lazily initialize the Alpaca broker.

*Line: 514*

---

## Function: 

Build the standardized order result dict.

*Line: 564*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 29*

---

## Function: 

*Line: 33*

---

