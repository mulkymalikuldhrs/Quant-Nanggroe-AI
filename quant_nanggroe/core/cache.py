from __future__ import annotations

import functools
import logging
import threading
import time
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class TTLCache:
    """Thread-safe in-memory TTL cache.

    Designed for wrapping API calls in scorers and data providers.
    Simpler than SQLite-backed DataCache — no I/O, no serialization
    overhead for small JSON payloads.

    Usage::

        cache = TTLCache(default_ttl=300)
        cache.set("fred:cpi", data, ttl=600)
        data = cache.get("fred:cpi")
    """

    def __init__(self, default_ttl: float = 300.0):
        self._default_ttl = default_ttl
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        expires_at = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            self._data[key] = (expires_at, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._data)


def cached(cache: TTLCache, key_prefix: str = "", ttl: Optional[float] = None):
    """Decorator that caches a function's return value by arguments.

    Usage::

        _cache = TTLCache(default_ttl=300)

        @cached(_cache, key_prefix="fred", ttl=600)
        def _fred_fetch(series_id: str, api_key: str) -> Optional[list[dict]]:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper  # type: ignore
    return decorator


# Module-level default instance
_cache = TTLCache(default_ttl=300.0)
cached_default = cached(_cache)
