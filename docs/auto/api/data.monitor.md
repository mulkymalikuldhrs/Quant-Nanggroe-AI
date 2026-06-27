# data.monitor

## Class: 

*Line: 46*

---

## Class: 

*Line: 56*

---

## Class: 

Tracks data freshness across all symbols and timeframes.

Thread-safe for concurrent access by multiple providers.

**Methods:** __init__, set_kill_switch, _get_kill_switch, check_and_trigger_kill_switch, record_fetch, record_batch, get_last_update, is_stale, get_stale_report, clear, remove_symbol

*Line: 64*

---

## Function: 

*Line: 70*

---

## Function: 

Bind a kill switch instance for auto-trigger on stale data.

*Line: 74*

---

## Function: 

Lazy import and return the kill switch module types.

*Line: 78*

---

## Function: 

Check data freshness and trigger kill switch if data is stale.

Thresholds (configurable via module constants):
- > 5 min  stale -> LEVEL_1 (reduce position size)
- > 15 min stale -> LEVEL_2 (close positions, stop new)
- > 60 min stale -> LEVEL_3 (emergency halt)

Returns the level triggered (as string), or None if no trigger.

*Line: 84*

---

## Function: 

Record that fresh data was fetched for a symbol at this timeframe.

*Line: 137*

---

## Function: 

Record a batch fetch for multiple symbols at once.

*Line: 143*

---

## Function: 

Get the last recorded update time for a symbol at a timeframe.

*Line: 150*

---

## Function: 

Check if a symbol is stale at a given timeframe.

Returns ``None`` if no data has ever been fetched.

*Line: 154*

---

## Function: 

Generate a freshness report for all tracked symbols.

If ``max_age_hours`` is set, it overrides all per-timeframe defaults.

*Line: 167*

---

## Function: 

Clear all tracked freshness data.

*Line: 205*

---

## Function: 

Remove a symbol from tracking.

*Line: 209*

---

