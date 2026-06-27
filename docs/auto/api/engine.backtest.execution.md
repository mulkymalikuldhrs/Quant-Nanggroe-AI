# engine.backtest.execution

## Class: 

Configuration for execution simulation.

Attributes:
    commission_rate: Commission rate as decimal (e.g. 0.001 = 0.1%).
    slippage_bps: Slippage in basis points (e.g. 5 = 0.05%).
    market: Market type string for market-specific rules.
    min_commission: Minimum commission per trade.
    market_impact_coeff: Market impact coefficient (0 = no impact).

*Line: 18*

---

## Class: 

Simulates realistic trade execution.

Models slippage, commission, and market impact for backtests.
Different markets have different default execution rules:

- Equity: T+1 settlement, SEC fees, exchange fees
- Crypto: 24/7, higher slippage, taker/maker fees
- Forex: Spread-based, rollover fees
- Futures: Contract multiplier, exchange fees

**Methods:** __init__, apply_slippage, calc_commission, calc_market_impact, simulate_fill

*Line: 36*

---

## Function: 

*Line: 56*

---

## Function: 

Apply slippage to execution price.

Slippage is always adverse:
- Buying: price increases
- Selling: price decreases

Args:
    price: Raw market price.
    direction: 1 for buying, -1 for selling.

Returns:
    Slipped execution price.

*Line: 73*

---

## Function: 

Calculate commission for a trade.

Commission is calculated as:
max(min_commission, commission_rate * trade_value)

Args:
    size: Trade size in units.
    price: Execution price.
    is_closing: Whether this is a closing trade.

Returns:
    Commission amount in currency.

*Line: 94*

---

## Function: 

Calculate market impact cost.

Market impact is modeled as a square-root function of participation rate:
impact = coeff * sqrt(size / avg_volume) * price

Args:
    size: Trade size.
    price: Current price.
    avg_volume: Average daily volume.

Returns:
    Market impact cost in price terms.

*Line: 117*

---

## Function: 

Simulate a complete order fill with all costs.

Args:
    price: Raw market price.
    direction: 1 for buy, -1 for sell.
    size: Order size.
    avg_volume: Average daily volume for impact calculation.

Returns:
    Dict with fill_price, commission, market_impact, total_cost.

*Line: 143*

---

