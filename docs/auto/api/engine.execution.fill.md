# engine.execution.fill

## Class: 

Execution quality metrics for a fill.

*Line: 16*

---

## Class: 

Fill tracking and reconciliation.

Tracks all fills, computes execution quality metrics,
and provides query capabilities for fill analysis.

**Methods:** __init__, record, get, get_by_order, get_by_symbol, compute_execution_quality, get_total_commission, get_total_slippage, get_fill_count, get_buys_sells

*Line: 29*

---

## Function: 

*Line: 36*

---

## Function: 

Record a fill.

Args:
    fill: Fill to record.

*Line: 40*

---

## Function: 

Get a fill by ID.

*Line: 51*

---

## Function: 

Get all fills for an order.

*Line: 55*

---

## Function: 

Get all fills for a symbol.

*Line: 59*

---

## Function: 

Compute execution quality metrics for a fill.

Args:
    fill: Fill to analyze.
    expected_price: Expected execution price.

Returns:
    ExecutionQuality with slippage and cost metrics.

*Line: 63*

---

## Function: 

Get total commission paid across all fills.

*Line: 95*

---

## Function: 

Get total slippage across all fills.

*Line: 99*

---

## Function: 

Get total number of fills.

*Line: 103*

---

## Function: 

Get count of buys and sells, optionally filtered by symbol.

Args:
    symbol: Optional symbol filter.

Returns:
    Dict with 'buys' and 'sells' counts.

*Line: 107*

---

