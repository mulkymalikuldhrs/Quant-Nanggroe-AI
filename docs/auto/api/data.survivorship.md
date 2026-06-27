# data.survivorship

## Class: 

*Line: 25*

---

## Class: 

*Line: 32*

---

## Class: 

Detects survivorship bias by tracking universe composition over time.

A universe is biased if a significant portion of historically tracked
symbols no longer exist in the current snapshot. The default threshold
is 10% missing symbols.

**Methods:** __init__, record_universe, get_universe, analyze, clear

*Line: 43*

---

## Function: 

*Line: 51*

---

## Function: 

Record a universe composition at a point in time.

Args:
    name: Universe identifier (e.g., "SP500", "NASDAQ100").
    symbols: Set of constituent symbols at this point in time.
    snapshot_date: Date of this snapshot. Defaults to today.
    source: Optional description of where this snapshot came from.

*Line: 55*

---

## Function: 

Get all recorded snapshots for a universe.

*Line: 81*

---

## Function: 

Analyze a universe for survivorship bias.

Compares the earliest (historical) snapshot against the latest
(current) snapshot. The proportion of symbols present historically
but missing today indicates the survivorship bias risk.

Returns ``None`` if fewer than 2 snapshots exist.

*Line: 85*

---

## Function: 

Clear all recorded snapshots.

*Line: 130*

---

