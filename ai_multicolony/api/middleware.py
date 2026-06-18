"""API middleware for authentication, rate limiting, logging, and error handling.

Designed to work with FastAPI or any ASGI-compatible framework.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ── Authentication Middleware ──────────────────────────────────────────────────


class AuthMiddleware:
    """JWT and API key authentication middleware.

    Supports two authentication methods:
    * **API Key** – sent as ``X-API-Key`` header
    * **Bearer Token** – sent as ``Authorization: Bearer <token>`` header

    Parameters
    ----------
    jwt_secret : str
        Secret key for JWT validation.
    api_key_enabled : bool
        Whether API key authentication is enabled.
    """

    def __init__(self, jwt_secret: str = "change-me", api_key_enabled: bool = True):
        self.jwt_secret = jwt_secret
        self.api_key_enabled = api_key_enabled
        self._api_keys: Dict[str, Dict[str, str]] = {}  # key → {agent_id, role}
        self._revoked_tokens: Set[str] = set()

    def register_api_key(self, key: str, agent_id: str = "", role: str = "agent") -> None:
        """Register an API key.

        Parameters
        ----------
        key : str
            The API key string.
        agent_id : str
            The agent ID associated with this key.
        role : str
            The role assigned to this key.
        """
        self._api_keys[key] = {"agent_id": agent_id, "role": role}

    def revoke_api_key(self, key: str) -> bool:
        """Revoke an API key."""
        return self._api_keys.pop(key, None) is not None

    def validate_api_key(self, key: str) -> Optional[Dict[str, str]]:
        """Validate an API key and return its metadata."""
        if key in self._revoked_tokens:
            return None
        return self._api_keys.get(key)

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT Bearer token.

        In production this would decode and verify the JWT signature.
        Returns decoded claims or None.
        """
        if token in self._revoked_tokens:
            return None

        # Simplified validation: token must be non-empty and reasonably long
        if not token or len(token) < 10:
            return None

        # Would decode JWT here:
        # payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        # Check expiry, issuer, etc.
        return {"sub": "agent", "role": "agent", "valid": True}

    def revoke_token(self, token: str) -> None:
        """Revoke a Bearer token."""
        self._revoked_tokens.add(token)

    def is_authenticated(self, headers: Dict[str, str]) -> bool:
        """Check if a request is authenticated.

        Checks both ``Authorization: Bearer ...`` and ``X-API-Key`` headers.
        """
        auth = headers.get("authorization", "") or headers.get("Authorization", "")
        api_key = headers.get("x-api-key", "") or headers.get("X-API-Key", "")

        if auth.startswith("Bearer ") and self.validate_token(auth[7:]):
            return True
        if self.api_key_enabled and api_key and self.validate_api_key(api_key):
            return True
        return False

    def get_identity(self, headers: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Extract the authenticated identity from request headers.

        Returns agent_id and role, or None if not authenticated.
        """
        auth = headers.get("authorization", "") or headers.get("Authorization", "")
        api_key = headers.get("x-api-key", "") or headers.get("X-API-Key", "")

        if auth.startswith("Bearer "):
            claims = self.validate_token(auth[7:])
            if claims:
                return {"agent_id": claims.get("sub", ""), "role": claims.get("role", "agent")}

        if self.api_key_enabled and api_key:
            key_info = self.validate_api_key(api_key)
            if key_info:
                return key_info

        return None


# ── Rate Limiting Middleware ──────────────────────────────────────────────────


class RateLimitMiddleware:
    """Sliding-window rate limiter.

    Supports per-IP and per-agent rate limiting.

    Parameters
    ----------
    requests_per_minute : int
        Maximum requests per minute per client.
    burst : int
        Maximum burst size.
    """

    def __init__(self, requests_per_minute: int = 60, burst: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self._counters: Dict[str, List[float]] = {}  # client_id → list of timestamps
        self._blocked: Dict[str, float] = {}  # client_id → block_until timestamp

    def is_allowed(self, client_id: str) -> bool:
        """Check if a request from the client is within rate limits.

        Uses a sliding window of 60 seconds.
        """
        now = time.time()

        # Check if blocked
        block_until = self._blocked.get(client_id, 0)
        if now < block_until:
            return False

        # Clean up old timestamps
        if client_id not in self._counters:
            self._counters[client_id] = []

        self._counters[client_id] = [
            t for t in self._counters[client_id] if now - t < 60
        ]

        # Check rate
        if len(self._counters[client_id]) >= self.requests_per_minute:
            return False

        # Check burst (requests in last second)
        recent = [t for t in self._counters[client_id] if now - t < 1]
        if len(recent) >= self.burst:
            return False

        # Record the request
        self._counters[client_id].append(now)
        return True

    def block(self, client_id: str, duration_s: float = 60) -> None:
        """Temporarily block a client."""
        self._blocked[client_id] = time.time() + duration_s

    def unblock(self, client_id: str) -> None:
        """Remove a client block."""
        self._blocked.pop(client_id, None)

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for a client in the current window."""
        now = time.time()
        timestamps = self._counters.get(client_id, [])
        recent = [t for t in timestamps if now - t < 60]
        return max(0, self.requests_per_minute - len(recent))

    def reset(self, client_id: Optional[str] = None) -> None:
        """Reset rate limit counters."""
        if client_id:
            self._counters.pop(client_id, None)
            self._blocked.pop(client_id, None)
        else:
            self._counters.clear()
            self._blocked.clear()


# ── Request Logging Middleware ─────────────────────────────────────────────────


class RequestLoggingMiddleware:
    """Middleware that logs request details for observability."""

    def __init__(self, log_body: bool = False, max_body_length: int = 1024):
        self.log_body = log_body
        self.max_body_length = max_body_length
        self._request_log: List[Dict[str, Any]] = []

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        client_id: str = "",
        body: str = "",
    ) -> None:
        """Log a completed request."""
        entry = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "client_id": client_id,
            "timestamp": time.time(),
        }
        if self.log_body and body:
            entry["body"] = body[: self.max_body_length]
        self._request_log.append(entry)

        # Also log to Python logger
        logger.info(
            "%s %s → %d (%.1fms) client=%s",
            method,
            path,
            status_code,
            duration_ms,
            client_id,
        )

    def get_recent_requests(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return recent request log entries."""
        return self._request_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Return request statistics."""
        if not self._request_log:
            return {"total_requests": 0}

        durations = [r["duration_ms"] for r in self._request_log]
        status_codes = [r["status_code"] for r in self._request_log]

        return {
            "total_requests": len(self._request_log),
            "avg_duration_ms": round(sum(durations) / len(durations), 2),
            "max_duration_ms": round(max(durations), 2),
            "error_count": sum(1 for s in status_codes if s >= 400),
            "success_rate": round(sum(1 for s in status_codes if s < 400) / len(status_codes), 3),
        }


# ── Error Handling Middleware ─────────────────────────────────────────────────


class ErrorHandlingMiddleware:
    """Centralized error handling and response formatting.

    Converts exceptions into structured JSON error responses.
    """

    # Map exception class names to HTTP status codes
    STATUS_MAP: Dict[str, int] = {
        "AgentNotFoundError": 404,
        "AgentTimeoutError": 408,
        "AgentStateError": 409,
        "ColonyNotFoundError": 404,
        "ColonyFullError": 409,
        "ToolNotFoundError": 404,
        "ToolPermissionError": 403,
        "MemoryError": 500,
        "MemoryCompactionError": 500,
        "MCPError": 502,
        "MCPProtocolError": 400,
        "SecurityError": 403,
        "PermissionDeniedError": 403,
        "AuthenticationError": 401,
        "ValueError": 400,
        "KeyError": 400,
        "TypeError": 400,
    }

    def __init__(self, include_traceback: bool = False):
        self.include_traceback = include_traceback

    def format_error(self, exc: Exception) -> Dict[str, Any]:
        """Format an exception into a structured error response dict."""
        exc_name = type(exc).__name__
        status_code = self.STATUS_MAP.get(exc_name, 500)

        error = {
            "error": str(exc),
            "code": getattr(exc, "code", exc_name.upper()),
            "status_code": status_code,
        }

        # Add extra fields from specific exception types
        if hasattr(exc, "agent_id"):
            error["agent_id"] = exc.agent_id
        if hasattr(exc, "colony_id"):
            error["colony_id"] = exc.colony_id
        if hasattr(exc, "tool_name"):
            error["tool_name"] = exc.tool_name
        if hasattr(exc, "required_level"):
            error["required_level"] = exc.required_level
        if hasattr(exc, "current_level"):
            error["current_level"] = exc.current_level

        if self.include_traceback:
            import traceback
            error["traceback"] = traceback.format_exc()

        return error

    def get_status_code(self, exc: Exception) -> int:
        """Get the HTTP status code for an exception."""
        exc_name = type(exc).__name__
        return self.STATUS_MAP.get(exc_name, 500)
