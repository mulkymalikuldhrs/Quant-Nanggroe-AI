# utils.time

## Class: 

Market type classification.

*Line: 15*

---

## Function: 

Check if a market is currently open.

Args:
    market_type: Type of market to check

Returns:
    True if the market is currently open

*Line: 45*

---

## Function: 

Get the schedule for a market type.

Args:
    market_type: Type of market

Returns:
    Schedule dictionary with timezone, open, close, weekends

*Line: 68*

---

## Function: 

Calculate the next market open time.

Args:
    market_type: Type of market

Returns:
    Datetime of the next market open

*Line: 81*

---

## Function: 

Infer market type from symbol format.

Args:
    symbol: Trading pair symbol

Returns:
    Inferred market type

*Line: 113*

---

