# engine.pattern_recorder.dtw

## Class: 

*Line: 15*

---

## Class: 

Dynamic Time Warping for pattern matching in financial time series.

Supports:
- Custom window constraints (Sakoe-Chiba band)
- Multi-dimensional DTW
- Derivative DTW (DDTW) for shape-based matching

**Methods:** __init__, compute, _backtrack, derivative_dtw, _compute_derivative, batch_match

*Line: 23*

---

## Function: 

*Line: 33*

---

## Function: 

Compute DTW distance between reference and query

*Line: 37*

---

## Function: 

Backtrack through cost matrix to find warping path

*Line: 75*

---

## Function: 

Derivative DTW — matches shape rather than absolute values

*Line: 98*

---

## Function: 

Compute local derivative of a series

*Line: 104*

---

## Function: 

Match reference against a database of patterns

*Line: 112*

---

