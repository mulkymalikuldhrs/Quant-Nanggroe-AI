# engine.pattern_recorder.matrix_profile

## Class: 

A repeated pattern discovered in the time series

*Line: 19*

---

## Class: 

An anomalous pattern in the time series

*Line: 31*

---

## Class: 

*Line: 41*

---

## Class: 

Matrix Profile-based pattern detection.

Falls back to numpy-only implementation if STUMPY is not available,
so it works in constrained environments.

**Methods:** __init__, _check_stumpy, compute, _numpy_mp, _compute_distances, _squared_distance, _find_motifs, _find_discords, find_motifs_of_length

*Line: 51*

---

## Function: 

*Line: 59*

---

## Function: 

*Line: 63*

---

## Function: 

Compute Matrix Profile and find motifs/discords

*Line: 71*

---

## Function: 

Numpy-only Matrix Profile computation (MASS algorithm)

*Line: 104*

---

## Function: 

Compute sliding dot product (MASS algorithm)

*Line: 149*

---

## Function: 

Compute average squared distance of matched motifs

*Line: 168*

---

## Function: 

Find top motifs (repeated patterns)

*Line: 176*

---

## Function: 

Find top discords (anomalies)

*Line: 221*

---

## Function: 

Find motifs at multiple window sizes

*Line: 259*

---

