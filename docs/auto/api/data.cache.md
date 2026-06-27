# data.cache

## Class: 

Thread-safe SQLite-backed persistent cache with TTL and namespace support.

Lazily opens the database connection on first use. Each entry has a
configurable TTL (time-to-live). Old entries are automatically purged
on write when the total count exceeds *max_entries*.

Parameters
----------
db_path:
    Path to the SQLite database file. If ``None``, resolves to
    ``<project_root>/cache/data_cache.sqlite``, or the path
    specified by the ``QNAI_CACHE_DIR`` environment variable.
max_entries:
    Maximum entries before auto-vacuum removes expired + oldest.

**Methods:** __init__, _ensure_connection, set, get, delete, clear_namespace, stats, clear, close, __enter__, __exit__, _maybe_vacuum

*Line: 31*

---

## Function: 

Resolve the cache database path.

Priority:
1. ``QNAI_CACHE_DIR`` env var → ``<dir>/data_cache.sqlite``
2. Project root (walk up from ``cache.py`` looking for ``pyproject.toml``)
   → ``<project_root>/cache/data_cache.sqlite``

*Line: 270*

---

## Function: 

*Line: 48*

---

## Function: 

*Line: 62*

---

## Function: 

Store *value* (must be JSON-serializable) with *ttl* in seconds.

*Line: 99*

---

## Function: 

Retrieve value for *key*, or ``None`` if missing or expired.

*Line: 121*

---

## Function: 

Remove a single entry.

*Line: 148*

---

## Function: 

Remove all entries whose key starts with *namespace*.

*Line: 158*

---

## Function: 

Return cache statistics.

Returns
-------
dict
    Keys: ``total_entries``, ``active_entries`` (not expired),
    ``db_size_mb``.

*Line: 173*

---

## Function: 

Remove ALL entries (use with care).

*Line: 205*

---

## Function: 

Close the database connection.

*Line: 215*

---

## Function: 

*Line: 226*

---

## Function: 

*Line: 229*

---

## Function: 

Remove expired + oldest entries when over *max_entries*.

*Line: 236*

---

