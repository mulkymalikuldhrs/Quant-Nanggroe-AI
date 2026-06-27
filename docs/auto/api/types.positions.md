# types.positions

## Class: 

Position direction.

*Line: 16*

---

## Class: 

A single trading position with full tracking.

Tracks entry, current state, PnL, and risk metrics.

**Methods:** update_price

*Line: 23*

---

## Class: 

Portfolio state with all positions and aggregate metrics.

The portfolio is the single source of truth for position state,
PnL, and risk calculations across all agents.

**Methods:** position_value, is_invested, recalculate

*Line: 73*

---

## Function: 

Update current price and recalculate PnL.

*Line: 54*

---

## Function: 

Total value of all open positions.

*Line: 104*

---

## Function: 

Whether the portfolio has any open positions.

*Line: 109*

---

## Function: 

Recalculate all derived portfolio metrics.

*Line: 113*

---

