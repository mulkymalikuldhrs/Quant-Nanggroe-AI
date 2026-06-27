# engine.pressure

## Class: 

Direction of market pressure.

*Line: 31*

---

## Class: 

Strength of market pressure.

*Line: 39*

---

## Class: 

Result from a pressure analysis.

*Line: 50*

---

## Class: 

A single OHLCV bar.

*Line: 68*

---

## Class: 

Configuration for pressure analysis.

*Line: 78*

---

## Class: 

Analyses market buy/sell pressure.

Uses volume analysis, price momentum, and order flow
approximation to determine market pressure.

Usage::

    engine = PressureEngine()
    bars = [OHLCVBar(open=100, high=102, low=99, close=101, volume=1000), ...]
    result = engine.analyze(bars, symbol="AAPL")

**Methods:** __init__, analyze, analyze_from_arrays, _compute_volume_imbalance, _compute_price_momentum, _compute_vwap_deviation, _compute_close_position, history, config, stats

*Line: 94*

---

## Class: 

Input dataclass for pressure engine analysis.

*Line: 348*

---

## Function: 

*Line: 107*

---

## Function: 

Analyse buy/sell pressure from OHLCV data.

Parameters
----------
bars:
    List of OHLCV bars (most recent last).
symbol:
    Symbol being analyzed.

Returns
-------
PressureResult
    Pressure analysis result.

*Line: 111*

---

## Function: 

Analyze pressure from separate price/volume arrays.

*Line: 215*

---

## Function: 

Compute volume imbalance (up volume vs down volume).

Returns
-------
float
    -1 to +1 (positive = more up volume).

*Line: 236*

---

## Function: 

Compute price momentum as rate of change.

*Line: 259*

---

## Function: 

Compute deviation of current price from VWAP.

*Line: 277*

---

## Function: 

Compute where the close sits relative to the bar's range.

Returns
-------
float
    0.0 = close at low, 1.0 = close at high, 0.5 = mid-range.

*Line: 298*

---

## Function: 

*Line: 323*

---

## Function: 

*Line: 327*

---

## Function: 

Pressure engine statistics.

*Line: 331*

---

