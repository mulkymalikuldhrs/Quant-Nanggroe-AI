# engine.strategy.strategies.market_making

## Class: 

Avellaneda-Stoikov market maker with inventory management.

The reservation price shifts away from mid-price based on
current inventory, risk aversion, and volatility.  Optimal
bid/ask quotes are placed symmetrically around the reservation
price with a spread governed by volatility and order arrival.

Parameters
----------
gamma : float
    Risk aversion coefficient (default 0.1).
kappa : float
    Order arrival rate (default 1.5).
sigma : float
    Volatility estimate (default 0.02).
inventory_target : float
    Desired inventory level (default 0.0).
max_inventory : float
    Maximum absolute position (default 100).
order_size : float
    Base quote size per level (default 1.0).
num_levels : int
    Quote depth on each side (default 1).
spread_multiplier : float
    Scale factor applied to the base spread (default 1.0).
transaction_cost_bps : float
    Round-trip transaction cost in basis points (default 10.0).
min_trade_interval_bars : int
    Minimum bars between trade signals (default 1).
symbol : str
    Trading symbol (default "ASSET").

**Methods:** __init__, required_columns, warmup_period, update_inventory, _reservation_price, _fee_adjustment, _base_spread, _inv_skew, _quote_levels, _estimate_sigma, generate_signal

*Line: 25*

---

## Function: 

*Line: 59*

---

## Function: 

*Line: 76*

---

## Function: 

*Line: 79*

---

## Function: 

Update internal inventory after a fill.

*Line: 86*

---

## Function: 

r = S - gamma * sigma^2 * q * T

*Line: 95*

---

## Function: 

(1/gamma) * ln(1 + gamma/kappa)

*Line: 99*

---

## Function: 

gamma * sigma^2 * T, scaled by the user multiplier.

*Line: 103*

---

## Function: 

*Line: 108*

---

## Function: 

Build ``num_levels`` of bid/ask quotes.

Returns a list of dicts, each containing:
    bid_price, ask_price, bid_size, ask_size

*Line: 115*

---

## Function: 

Rolling 20-bar close-to-close volatility, falling back to param.

*Line: 148*

---

## Function: 

*Line: 160*

---

