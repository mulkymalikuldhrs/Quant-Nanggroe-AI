"""Persistence Layer — Redis-backed with graceful fallback.

Provides a unified persistence interface with three backends:
- RedisBackend: Production-grade persistence using redis-py with connection
  pooling, TTL support, and JSON serialization.
- FileBackend: Fallback persistence using JSON files on disk.
- MemoryBackend: In-memory dict-based backend for testing.

Backend selection is controlled by the PERSISTENCE_BACKEND environment
variable (redis|file|memory, default=file). If Redis is requested but
unavailable, the system gracefully falls back to FileBackend with a
warning.

Usage:
    from quant_nanggroe.engine.persistence import get_persistence_backend

    backend = get_persistence_backend()
    backend.set("risk:daily_pnl", -500.0, ttl=86400)
    value = backend.get("risk:daily_pnl")
    backend.delete("risk:daily_pnl")
"""

from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default data directory for FileBackend
DEFAULT_DATA_DIR = "data/persistence"


class PersistenceBackend(ABC):
    """Abstract base class for persistence backends.

    All backends must implement the core CRUD operations plus
    key enumeration and health checking.
    """

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key.

        Args:
            key: The key to look up.

        Returns:
            The stored value (deserialized), or None if not found.
        """

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value with optional TTL.

        Args:
            key: The key to store under.
            value: The value to store (must be JSON-serializable).
            ttl: Optional time-to-live in seconds.

        Returns:
            True if successful, False otherwise.
        """

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key.

        Args:
            key: The key to delete.

        Returns:
            True if the key existed and was deleted, False otherwise.
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: The key to check.

        Returns:
            True if the key exists, False otherwise.
        """

    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """List keys matching a pattern.

        Args:
            pattern: Glob-style pattern (default: all keys).

        Returns:
            List of matching key names.
        """

    def health_check(self) -> Dict[str, Any]:
        """Check backend health.

        Returns:
            Dict with 'healthy' bool and optional 'details' dict.
        """
        return {"healthy": True, "backend": self.__class__.__name__}

    def get_with_default(self, key: str, default: Any = None) -> Any:
        """Get a value, returning default if not found.

        Args:
            key: The key to look up.
            default: Value to return if key not found.

        Returns:
            The stored value or default.
        """
        value = self.get(key)
        return value if value is not None else default

    def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Store multiple key-value pairs.

        Args:
            mapping: Dict of key-value pairs to store.
            ttl: Optional TTL in seconds for all keys.

        Returns:
            True if all operations succeeded, False otherwise.
        """
        success = True
        for k, v in mapping.items():
            if not self.set(k, v, ttl=ttl):
                success = False
        return success

    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys.

        Args:
            keys: List of keys to delete.

        Returns:
            Number of keys that were actually deleted.
        """
        count = 0
        for k in keys:
            if self.delete(k):
                count += 1
        return count


class MemoryBackend(PersistenceBackend):
    """In-memory persistence backend for testing.

    Thread-safe using a lock. Supports TTL via timestamp tracking.
    All data is lost on process exit — use only for tests.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}  # key -> expiry timestamp
        self._lock = threading.Lock()

    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key in self._ttl:
            if datetime.now().timestamp() > self._ttl[key]:
                del self._store[key]
                del self._ttl[key]
                return True
        return False

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            self._is_expired(key)
            return self._store.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            self._store[key] = value
            if ttl is not None:
                self._ttl[key] = datetime.now().timestamp() + ttl
            elif key in self._ttl:
                del self._ttl[key]
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._ttl.pop(key, None)
                return True
            return False

    def exists(self, key: str) -> bool:
        with self._lock:
            self._is_expired(key)
            return key in self._store

    def keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            # Expire all keys first
            expired = [k for k in list(self._ttl.keys())
                       if datetime.now().timestamp() > self._ttl[k]]
            for k in expired:
                self._store.pop(k, None)
                del self._ttl[k]

            if pattern == "*":
                return list(self._store.keys())

            # Simple glob matching
            import fnmatch
            return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]

    def clear(self) -> None:
        """Clear all data (useful for test teardown)."""
        with self._lock:
            self._store.clear()
            self._ttl.clear()


class FileBackend(PersistenceBackend):
    """File-based persistence backend using JSON files.

    Each key is stored as a separate JSON file in the data directory.
    Supports TTL by storing expiry timestamps in a metadata file.
    Suitable for development and as a Redis fallback.
    """

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self._data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._meta_path = self._data_dir / "_meta.json"
        self._lock = threading.Lock()

    def _key_to_path(self, key: str) -> Path:
        """Convert a key to a safe file path."""
        # Replace path separators and special chars
        safe_key = key.replace("/", "_SLASH_").replace("\\", "_BSLASH_").replace(":", "_COLON_")
        return self._data_dir / f"{safe_key}.json"

    def _load_meta(self) -> Dict[str, float]:
        """Load TTL metadata."""
        if self._meta_path.exists():
            try:
                with open(self._meta_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_meta(self, meta: Dict[str, float]) -> None:
        """Save TTL metadata."""
        try:
            with open(self._meta_path, "w") as f:
                json.dump(meta, f)
        except OSError as e:
            logger.warning("Failed to save TTL metadata: %s", e)

    def _is_expired(self, key: str, meta: Dict[str, float]) -> bool:
        """Check if a key has expired based on metadata."""
        if key in meta:
            if datetime.now().timestamp() > meta[key]:
                # Clean up expired key
                path = self._key_to_path(key)
                if path.exists():
                    path.unlink()
                del meta[key]
                self._save_meta(meta)
                return True
        return False

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            meta = self._load_meta()
            if self._is_expired(key, meta):
                return None

            path = self._key_to_path(key)
            if not path.exists():
                return None

            try:
                with open(path, "r") as f:
                    data = json.load(f)
                return data.get("value")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to read key %s: %s", key, e)
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            path = self._key_to_path(key)
            try:
                data = {
                    "value": value,
                    "updated_at": datetime.now().isoformat(),
                }
                with open(path, "w") as f:
                    json.dump(data, f, indent=2, default=str)

                # Handle TTL
                meta = self._load_meta()
                if ttl is not None:
                    meta[key] = datetime.now().timestamp() + ttl
                elif key in meta:
                    del meta[key]
                self._save_meta(meta)

                return True
            except (OSError, TypeError) as e:
                logger.warning("Failed to write key %s: %s", key, e)
                return False

    def delete(self, key: str) -> bool:
        with self._lock:
            path = self._key_to_path(key)
            existed = path.exists()
            if existed:
                path.unlink()

            # Clean up TTL metadata
            meta = self._load_meta()
            if key in meta:
                del meta[key]
                self._save_meta(meta)

            return existed

    def exists(self, key: str) -> bool:
        with self._lock:
            meta = self._load_meta()
            if self._is_expired(key, meta):
                return False
            return self._key_to_path(key).exists()

    def keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            meta = self._load_meta()

            # Clean expired keys first
            expired_keys = []
            now_ts = datetime.now().timestamp()
            for k, expiry in list(meta.items()):
                if now_ts > expiry:
                    expired_keys.append(k)
            for k in expired_keys:
                path = self._key_to_path(k)
                if path.exists():
                    path.unlink()
                del meta[k]
            if expired_keys:
                self._save_meta(meta)

            # List all keys from files
            result = []
            import fnmatch
            for path in self._data_dir.glob("*.json"):
                if path.name == "_meta.json":
                    continue
                # Convert filename back to key
                key = path.stem
                key = key.replace("_SLASH_", "/").replace("_BSLASH_", "\\").replace("_COLON_", ":")
                if pattern == "*" or fnmatch.fnmatch(key, pattern):
                    result.append(key)
            return result

    def health_check(self) -> Dict[str, Any]:
        """Check FileBackend health by verifying directory is writable."""
        try:
            test_path = self._data_dir / "_health_check.tmp"
            test_path.write_text("ok")
            test_path.unlink()
            return {
                "healthy": True,
                "backend": "FileBackend",
                "data_dir": str(self._data_dir),
            }
        except OSError as e:
            return {
                "healthy": False,
                "backend": "FileBackend",
                "data_dir": str(self._data_dir),
                "error": str(e),
            }


class RedisBackend(PersistenceBackend):
    """Redis-backed persistence with connection pooling and TTL support.

    Uses lazy imports for redis-py so the module can be imported even
    when redis is not installed. Connection is configured via
    environment variables:
    - REDIS_HOST (default: localhost)
    - REDIS_PORT (default: 6379)
    - REDIS_DB (default: 0)
    - REDIS_PASSWORD (default: None)
    - REDIS_URL (overrides individual settings if set)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        url: Optional[str] = None,
        prefix: str = "qna:",
    ) -> None:
        # Lazy import — redis may not be installed
        try:
            import redis
        except ImportError:
            raise ImportError(
                "redis-py is required for RedisBackend. "
                "Install with: pip install redis>=5.0.0"
            )

        self._prefix = prefix

        # Build connection pool
        if url:
            self._pool = redis.ConnectionPool.from_url(url, decode_responses=True)
        else:
            self._pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                max_connections=10,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

        self._client = redis.Redis(connection_pool=self._pool)

    def _prefixed(self, key: str) -> str:
        """Add namespace prefix to key."""
        return f"{self._prefix}{key}"

    def _unprefixed(self, key: str) -> str:
        """Remove namespace prefix from key."""
        if key.startswith(self._prefix):
            return key[len(self._prefix):]
        return key

    def get(self, key: str) -> Optional[Any]:
        try:
            data = self._client.get(self._prefixed(key))
            if data is None:
                return None
            return json.loads(data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Redis GET failed for key %s: %s", key, e)
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized = json.dumps(value, default=str)
            px = None
            if ttl is not None:
                px = ttl * 1000  # Redis uses milliseconds for PX
            return self._client.set(self._prefixed(key), serialized, px=px)
        except (TypeError, Exception) as e:
            logger.warning("Redis SET failed for key %s: %s", key, e)
            return False

    def delete(self, key: str) -> bool:
        try:
            return self._client.delete(self._prefixed(key)) > 0
        except Exception as e:
            logger.warning("Redis DELETE failed for key %s: %s", key, e)
            return False

    def exists(self, key: str) -> bool:
        try:
            return self._client.exists(self._prefixed(key)) > 0
        except Exception as e:
            logger.warning("Redis EXISTS failed for key %s: %s", key, e)
            return False

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            prefixed_pattern = self._prefixed(pattern)
            raw_keys = self._client.keys(prefixed_pattern)
            return [self._unprefixed(k) for k in raw_keys]
        except Exception as e:
            logger.warning("Redis KEYS failed for pattern %s: %s", pattern, e)
            return []

    def health_check(self) -> Dict[str, Any]:
        try:
            self._client.ping()
            info = self._client.info("server")
            return {
                "healthy": True,
                "backend": "RedisBackend",
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", "unknown"),
            }
        except Exception as e:
            return {
                "healthy": False,
                "backend": "RedisBackend",
                "error": str(e),
            }

    def close(self) -> None:
        """Close the connection pool."""
        try:
            self._pool.disconnect()
        except Exception:
            pass


def get_persistence_backend(
    backend_name: Optional[str] = None,
    **kwargs: Any,
) -> PersistenceBackend:
    """Factory function to create the appropriate persistence backend.

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
    """
    name = backend_name or os.environ.get("PERSISTENCE_BACKEND", "file").lower().strip()

    if name == "memory":
        logger.info("Using MemoryBackend for persistence")
        return MemoryBackend()

    if name == "redis":
        try:
            host = kwargs.pop("host", os.environ.get("REDIS_HOST", "localhost"))
            port = int(kwargs.pop("port", os.environ.get("REDIS_PORT", 6379)))
            db = int(kwargs.pop("db", os.environ.get("REDIS_DB", 0)))
            password = kwargs.pop("password", os.environ.get("REDIS_PASSWORD", None))
            url = kwargs.pop("url", os.environ.get("REDIS_URL", None))
            prefix = kwargs.pop("prefix", "qna:")

            backend = RedisBackend(
                host=host, port=port, db=db,
                password=password, url=url, prefix=prefix,
            )

            # Verify connection
            health = backend.health_check()
            if health.get("healthy"):
                logger.info("Using RedisBackend for persistence (connected)")
                return backend
            else:
                logger.warning(
                    "Redis health check failed: %s. Falling back to FileBackend.",
                    health.get("error", "unknown"),
                )
                return _fallback_file_backend()

        except ImportError:
            logger.warning(
                "redis-py not installed. Falling back to FileBackend. "
                "Install with: pip install redis>=5.0.0"
            )
            return _fallback_file_backend()
        except Exception as e:
            logger.warning(
                "Redis connection failed: %s. Falling back to FileBackend.",
                e,
            )
            return _fallback_file_backend()

    # Default: file
    if name == "file":
        data_dir = kwargs.pop("data_dir", None)
        logger.info("Using FileBackend for persistence (dir=%s)", data_dir or DEFAULT_DATA_DIR)
        return FileBackend(data_dir=data_dir)

    logger.warning("Unknown backend '%s'. Falling back to FileBackend.", name)
    return _fallback_file_backend()


def _fallback_file_backend() -> FileBackend:
    """Create a FileBackend as fallback."""
    return FileBackend()
