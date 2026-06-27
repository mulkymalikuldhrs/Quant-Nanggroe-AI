# utils.validation

## Function: 

Validate a trading symbol format.

Args:
    symbol: Symbol to validate
    market: Optional market type hint ('crypto', 'stocks', 'forex')

Returns:
    True if the symbol is valid

*Line: 21*

---

## Function: 

Validate a timeframe string.

Args:
    timeframe: Timeframe to validate

Returns:
    True if the timeframe is valid

*Line: 52*

---

## Function: 

Validate a trade quantity.

Args:
    quantity: Quantity to validate
    min_qty: Minimum allowed quantity

Returns:
    True if the quantity is valid

*Line: 69*

---

## Function: 

Validate a price value.

Args:
    price: Price to validate

Returns:
    True if the price is valid (positive and finite)

*Line: 83*

---

