# agents.trader.tools

## Function: 

Lazy-load ExecutionTool from shared tools.

*Line: 36*

---

## Function: 

Lazy-load ExecutionManager from engine.

*Line: 48*

---

## Function: 

Lazy-load PaperExchangeBroker for position/portfolio queries.

*Line: 62*

---

## Function: 

*Line: 74*

---

## Function: 

*Line: 92*

---

## Function: 

*Line: 107*

---

## Function: 

Place a trading order.

PRODUCTION: Uses ExecutionTool for real order routing through
PaperBroker (or live broker when configured).
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Trading symbol (e.g., AAPL, BTCUSDT)
    action: Trade action (BUY, SELL, SHORT, COVER)
    quantity: Number of shares/contracts
    order_type: Order type (market, limit, stop, stop_limit)
    price: Limit price (required for limit orders)
    stop_loss: Stop loss price
    take_profit: Take profit price

Returns:
    JSON string with order confirmation

*Line: 128*

---

## Function: 

Get current position information for a symbol.

PRODUCTION: Uses PaperBroker for real position data.
Falls back to mock data only in _MOCK_MODE.

Args:
    symbol: Trading symbol

Returns:
    JSON string with position details

*Line: 238*

---

## Function: 

Get current portfolio overview.

PRODUCTION: Uses PaperBroker for real portfolio data.
Falls back to mock data only in _MOCK_MODE.

Returns:
    JSON string with portfolio summary

*Line: 287*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 20*

---

## Function: 

*Line: 24*

---

