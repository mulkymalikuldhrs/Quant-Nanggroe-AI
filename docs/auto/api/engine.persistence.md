# engine.persistence

## Class: 

Abstract base class for persistence backends.

All backends must implement the core CRUD operations plus
key enumeration and health checking.

**Methods:** get, set, delete, exists, keys, health_check, get_with_default, set_many, delete_many

*Line: 40*

---

## Class: 

In-memory persistence backend for testing.

Thread-safe using a lock. Supports TTL via timestamp tracking.
All data is lost on process exit — use only for tests.

**Methods:** __init__, _is_expired, get, set, delete, exists, keys, clear

*Line: 157*

---

## Class: 

File-based persistence backend using JSON files.

Each key is stored as a separate JSON file in the data directory.
Supports TTL by storing expiry timestamps in a metadata file.
Suitable for development and as a Redis fallback.

**Methods:** __init__, _key_to_path, _load_meta, _save_meta, _is_expired, get, set, delete, exists, keys, health_check

*Line: 228*

---

## Class: 

Redis-backed persistence with connection pooling and TTL support.

Uses lazy imports for redis-py so the module can be imported even
when redis is not installed. Connection is configured via
environment variables:
- REDIS_HOST (default: localhost)
- REDIS_PORT (default: 6379)
- REDIS_DB (default: 0)
- REDIS_PASSWORD (default: None)
- REDIS_URL (overrides individual settings if set)

**Methods:** __init__, _prefixed, _unprefixed, get, set, delete, exists, keys, health_check, close

*Line: 394*

---

## Function: 

Factory function to create the appropriate persistence backend.

Backend selection priority:
1. Explicit backend_name argument
2. PERSISTENCE_BACKEND environment variable
3. Default: "file"

If Redis is requested but unavailable, gracefully falls back
to FileBackend with a warning.

Args:
    backend_name: Explicitly select backend (redis/file/memory).
    **kwargs: Additional arguments passed to backend constructor.

Returns:
    Configured PersistenceBackend instance.

*Line: 524*

---

## Function: 

Create a FileBackend as fallback.

*Line: 600*

---

## Function: 

Retrieve a value by key.

Args:
    key: The key to look up.

Returns:
    The stored value (deserialized), or None if not found.

*Line: 48*

---

## Function: 

Store a value with optional TTL.

Args:
    key: The key to store under.
    value: The value to store (must be JSON-serializable).
    ttl: Optional time-to-live in seconds.

Returns:
    True if successful, False otherwise.

*Line: 59*

---

## Function: 

Delete a key.

Args:
    key: The key to delete.

Returns:
    True if the key existed and was deleted, False otherwise.

*Line: 72*

---

## Function: 

Check if a key exists.

Args:
    key: The key to check.

Returns:
    True if the key exists, False otherwise.

*Line: 83*

---

## Function: 

List keys matching a pattern.

Args:
    pattern: Glob-style pattern (default: all keys).

Returns:
    List of matching key names.

*Line: 94*

---

## Function: 

Check backend health.

Returns:
    Dict with 'healthy' bool and optional 'details' dict.

*Line: 104*

---

## Function: 

Get a value, returning default if not found.

Args:
    key: The key to look up.
    default: Value to return if key not found.

Returns:
    The stored value or default.

*Line: 112*

---

## Function: 

Store multiple key-value pairs.

Args:
    mapping: Dict of key-value pairs to store.
    ttl: Optional TTL in seconds for all keys.

Returns:
    True if all operations succeeded, False otherwise.

*Line: 125*

---

## Function: 

Delete multiple keys.

Args:
    keys: List of keys to delete.

Returns:
    Number of keys that were actually deleted.

*Line: 141*

---

## Function: 

*Line: 164*

---

## Function: 

Check if a key has expired.

*Line: 169*

---

## Function: 

*Line: 178*

---

## Function: 

*Line: 183*

---

## Function: 

*Line: 192*

---

## Function: 

*Line: 200*

---

## Function: 

*Line: 205*

---

## Function: 

Clear all data (useful for test teardown).

*Line: 221*

---

## Function: 

*Line: 236*

---

## Function: 

Convert a key to a safe file path.

*Line: 242*

---

## Function: 

Load TTL metadata.

*Line: 248*

---

## Function: 

Save TTL metadata.

*Line: 258*

---

## Function: 

Check if a key has expired based on metadata.

*Line: 266*

---

## Function: 

*Line: 279*

---

## Function: 

*Line: 297*

---

## Function: 

*Line: 321*

---

## Function: 

*Line: 336*

---

## Function: 

*Line: 343*

---

## Function: 

Check FileBackend health by verifying directory is writable.

*Line: 374*

---

## Function: 

*Line: 407*

---

## Function: 

Add namespace prefix to key.

*Line: 445*

---

## Function: 

Remove namespace prefix from key.

*Line: 449*

---

## Function: 

*Line: 455*

---

## Function: 

*Line: 465*

---

## Function: 

*Line: 476*

---

## Function: 

*Line: 483*

---

## Function: 

*Line: 490*

---

## Function: 

*Line: 499*

---

## Function: 

Close the connection pool.

*Line: 516*

---

