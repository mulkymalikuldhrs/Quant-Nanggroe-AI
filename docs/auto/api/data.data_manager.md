# data.data_manager

## Class: 

Market data provider categories.

*Line: 42*

---

## Class: 

A registered data provider with failover priority.

Lower ``priority`` values are tried first during failover.

*Line: 54*

---

## Class: 

Cached DataFrame with expiration timestamp.

*Line: 67*

---

## Class: 

Unified data interface — singleton.

Providers register themselves with a type and priority.
``get_ohlcv`` automatically tries providers in priority order,
falling back on failure. Results are cached with configurable TTL.

**Methods:** __new__, __init__, register, registered, _cache_key, _cache_get, _cache_set, _cache_invalidate, get_ohlcv, subscribe, unsubscribe, _notify, _normalize

*Line: 79*

---

## Function: 

*Line: 89*

---

## Function: 

*Line: 95*

---

## Function: 

Register a data provider.

Args:
    name: Human-readable provider identifier.
    instance: Provider object that implements ``fetch_ohlcv``.
    provider_type: Category of market data.
    priority: Lower values are preferred during failover.

*Line: 108*

---

## Function: 

List registered providers, optionally filtered by type.

*Line: 134*

---

## Function: 

*Line: 144*

---

## Function: 

*Line: 154*

---

## Function: 

*Line: 163*

---

## Function: 

*Line: 166*

---

## Function: 

Fetch OHLCV candles with automatic failover and caching.

Tries registered providers in priority order. If the primary
provider fails, falls back to the next. Raises after all
providers fail.

Returns:
    DataFrame with columns: timestamp, open, high, low, close, volume.
    Timestamps are timezone-naive UTC.

*Line: 176*

---

## Function: 

Register a callback for real-time candle updates.

The callback receives a single-row DataFrame with the standard
candle columns whenever the provider pushes an update.

*Line: 255*

---

## Function: 

Remove a previously registered callback.

*Line: 264*

---

## Function: 

Push a candle update to all subscribers for the symbol.

*Line: 271*

---

## Function: 

Standardize a raw provider DataFrame into the canonical format.

Expected output columns: timestamp, open, high, low, close, volume.
Timestamps are converted to UTC datetime with no timezone info.

*Line: 286*

---

