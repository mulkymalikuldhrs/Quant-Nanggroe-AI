"""Caching layer with TTL support.

Supports Redis as primary backend with file-based and in-memory fallbacks.
Inspired by the cache system from ai-hedge-fund and Quant-Nanggroe-AI's
AutoSwitch health-based caching.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from quant_nanggroe.config.settings import get_settings

logger = logging.getLogger("quant_nanggroe.data.cache")


class CacheBackend:
    """Abstract cache backend interface."""

    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    def set(self, key: str, value: str, ttl: int = 300) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """In-memory cache with TTL support.

    Suitable for development and testing. Data is lost on process restart.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: str, ttl: int = 300) -> None:
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None


class FileCache(CacheBackend):
    """File-based cache with TTL support.

    Stores cache entries as JSON files in a configurable directory.
    Suitable for single-process production deployments without Redis.
    """

    def __init__(self, cache_dir: str = ".cache/quant_nanggroe") -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return self._cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[str]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() > data.get("expires_at", 0):
                path.unlink(missing_ok=True)
                return None
            return data["value"]
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, key: str, value: str, ttl: int = 300) -> None:
        path = self._path(key)
        data = {"value": value, "expires_at": time.time() + ttl}
        path.write_text(json.dumps(data))

    def delete(self, key: str) -> None:
        path = self._path(key)
        path.unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None


class RedisCache(CacheBackend):
    """Redis cache backend with TTL support.

    Preferred for production deployments with multiple processes.
    """

    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        self._url = url
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import redis

            self._client = redis.from_url(self._url, decode_responses=True)
            return self._client
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            return None

    def get(self, key: str) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return None
        try:
            return client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: str, ttl: int = 300) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, key: str) -> None:
        client = self._get_client()
        if client is None:
            return
        try:
            client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def exists(self, key: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            return bool(client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False


class DataCache:
    """High-level cache interface with automatic backend selection.

    Selects backend based on settings:
    - "redis": RedisCache (preferred for production)
    - "file": FileCache (single-process production)
    - "memory": MemoryCache (development/testing)
    """

    def __init__(self) -> None:
        settings = get_settings()
        backend = settings.cache_backend

        if backend == "redis" and settings.redis_url:
            self._backend: CacheBackend = RedisCache(url=settings.redis_url)
        elif backend == "file":
            self._backend = FileCache()
        else:
            self._backend = MemoryCache()

        self._default_ttl = settings.cache_ttl
        self._enabled = settings.cache_enabled

    @staticmethod
    def make_key(prefix: str, **kwargs) -> str:
        """Generate a deterministic cache key from prefix and kwargs."""
        parts = [prefix]
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}={v}")
        return ":".join(parts)

    def get_json(self, key: str) -> Optional[dict]:
        """Get a JSON-deserialized value from cache."""
        if not self._enabled:
            return None
        raw = self._backend.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        """Set a JSON-serializable value in cache."""
        if not self._enabled:
            return
        self._backend.set(key, json.dumps(value, default=str), ttl or self._default_ttl)

    def get_raw(self, key: str) -> Optional[str]:
        """Get a raw string value from cache."""
        if not self._enabled:
            return None
        return self._backend.get(key)

    def set_raw(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """Set a raw string value in cache."""
        if not self._enabled:
            return
        self._backend.set(key, value, ttl or self._default_ttl)

    def invalidate(self, key: str) -> None:
        """Remove a key from cache."""
        self._backend.delete(key)
