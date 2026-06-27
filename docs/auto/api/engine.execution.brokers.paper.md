# engine.execution.brokers.paper

## Class: 

Paper trading broker with realistic simulation.

Simulates:
- Market/Limit/Stop order execution
- Configurable slippage (basis points)
- Commission (percentage or fixed)
- Partial fills
- Order rejections (insufficient funds, etc.)

**Methods:** __init__, name, is_connected, set_price, _apply_slippage, _update_position

*Line: 33*

---

## Function: 

*Line: 44*

---

## Function: 

*Line: 63*

---

## Function: 

*Line: 67*

---

## Function: 

Set the current price for a symbol (for simulation).

Args:
    symbol: Trading symbol.
    price: Current market price.

*Line: 188*

---

## Function: 

Apply slippage to price.

Buying: price increases (adverse)
Selling: price decreases (adverse)

*Line: 209*

---

## Function: 

Update position after order fill.

*Line: 221*

---

