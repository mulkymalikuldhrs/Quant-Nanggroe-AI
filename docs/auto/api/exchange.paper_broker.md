# exchange.paper_broker

## Class: 

Paper trading exchange broker with realistic simulation.

Simulates a full exchange with order execution, market data generation,
position tracking, and portfolio management.  Designed for backtesting,
strategy development, and integration testing.

Parameters
----------
initial_capital:
    Starting cash balance in quote currency.
commission_rate:
    Commission as a fraction of trade value (e.g. 0.001 = 0.1%).
slippage_bps:
    Slippage in basis points (e.g. 5 = 0.05%).
min_commission:
    Minimum commission per trade.
default_price:
    Default price for symbols that have not been explicitly set.

Examples
--------
.. code-block:: python

    broker = PaperExchangeBroker(initial_capital=100_000)
    await broker.connect()
    broker.set_price("BTC/USDT", 42000.0)

    order = await broker.place_order(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.5,
    )
    assert order.status == OrderStatus.FILLED

**Methods:** __init__, is_connected, state, name, set_price, get_price, add_ohlcv, _update_position, _apply_slippage, cash, total_commission, total_slippage, realized_pnl, order_count, pending_order_count, check_pending_orders

*Line: 51*

---

## Function: 

*Line: 88*

---

## Function: 

*Line: 157*

---

## Function: 

*Line: 161*

---

## Function: 

*Line: 165*

---

## Function: 

Set the simulated market price for a symbol.

Also updates all positions tracking that symbol.

Args:
    symbol: Trading pair (e.g. ``"BTC/USDT"``).
    price: New market price.

*Line: 172*

---

## Function: 

Get the current simulated price for a symbol.

*Line: 202*

---

## Function: 

Add an OHLCV candle to the simulated history.

*Line: 206*

---

## Function: 

Update the position book after an order fill.

*Line: 653*

---

## Function: 

Apply slippage to price — buying pushes price up, selling pushes down.

*Line: 780*

---

## Function: 

Current cash balance.

*Line: 793*

---

## Function: 

Total commission paid.

*Line: 798*

---

## Function: 

Total slippage incurred.

*Line: 803*

---

## Function: 

Total realized P&L.

*Line: 808*

---

## Function: 

Total number of orders placed.

*Line: 813*

---

## Function: 

Number of currently pending orders.

*Line: 818*

---

## Function: 

Check and fill any pending orders whose conditions are now met.

Call this after :meth:`set_price` to simulate limit/stop triggers.

Returns:
    Number of orders that were filled.

*Line: 822*

---

