"""MCPServer – JSON-RPC 2.0 server with tool registration, permission
enforcement, rate limiting, circuit breaking, audit logging, and
transport support.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from .protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCBatchRequest,
    JSONRPCBatchResponse,
    JSONRPCError,
    JSONRPCErrorCodes,
    parse_request,
    parse_batch_request,
    parse_message,
    make_success_response,
    make_error_response,
    make_response,
    make_notification,
)
from .permissions import PermissionEngine

logger = logging.getLogger(__name__)


# ── Rate limiter ─────────────────────────────────────────────────

class RateLimiter:
    """Token-bucket rate limiter with global and per-agent windows."""

    def __init__(self, rate: float = 60.0, burst: int = 10, per_agent_limit: int = 120):
        self.rate = rate
        self.burst = burst
        self.per_agent_limit = per_agent_limit
        self._tokens = float(burst)
        self._last_refill = time.time()
        self._per_agent: Dict[str, List[float]] = {}

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def allow(self, agent_id: str = "") -> bool:
        """Check if a global call is allowed."""
        self._refill()
        if self._tokens < 1:
            return False
        self._tokens -= 1
        return True

    def allow_agent(self, agent_id: str, max_per_minute: int = 0) -> bool:
        """Check if a specific agent is within their per-minute limit."""
        limit = max_per_minute or self.per_agent_limit
        now = time.time()
        if agent_id not in self._per_agent:
            self._per_agent[agent_id] = []

        timestamps = self._per_agent[agent_id]
        # Prune old timestamps
        timestamps[:] = [t for t in timestamps if now - t < 60.0]

        if len(timestamps) >= limit:
            self._per_agent[agent_id] = timestamps
            return False

        timestamps.append(now)
        self._per_agent[agent_id] = timestamps
        return True

    def agent_remaining(self, agent_id: str) -> int:
        """Return remaining calls for an agent in the current window."""
        now = time.time()
        timestamps = self._per_agent.get(agent_id, [])
        timestamps = [t for t in timestamps if now - t < 60.0]
        return max(0, self.per_agent_limit - len(timestamps))


# ── Circuit breaker (per-tool) ───────────────────────────────────

class CircuitBreaker:
    """Circuit breaker for individual tools."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self._state = "closed"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> str:
        if self._state == "open" and self._last_failure_time:
            if (time.time() - self._last_failure_time) > self.timeout:
                self._state = "half_open"
        return self._state

    def can_execute(self) -> bool:
        return self.state in ("closed", "half_open")

    def record_success(self) -> None:
        self._success_count += 1
        if self._state == "half_open":
            self._state = "closed"
            self._failure_count = 0

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    def reset(self) -> None:
        self._state = "closed"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout,
        }


# ── Tool schema record ──────────────────────────────────────────

class ToolRecord:
    """Internal record for a registered tool on the server."""

    __slots__ = ("name", "handler", "schema", "required_level", "description")

    def __init__(
        self,
        name: str,
        handler: Callable,
        schema: Optional[Dict] = None,
        required_level: int = 1,
        description: str = "",
    ) -> None:
        self.name = name
        self.handler = handler
        self.schema = schema or {}
        self.required_level = required_level
        self.description = description


# ── MCP Server ───────────────────────────────────────────────────

class MCPServer:
    """MCP Server: JSON-RPC 2.0 tool server with permission engine,
    circuit breaker, rate limiting, and audit logging.

    Supported methods
    -----------------
    ping            : health check
    tools/list      : list registered tools
    tools/describe  : get schema for a tool
    tools/call      : invoke a tool

    Transport
    ---------
    The server is transport-agnostic.  Call ``handle_raw`` with incoming
    bytes (from stdio, HTTP, WebSocket, etc.) and send back the response
    bytes.
    """

    def __init__(
        self,
        permission_engine: Optional[PermissionEngine] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        self.permission_engine = permission_engine or PermissionEngine()
        self.rate_limiter = rate_limiter or RateLimiter()
        self._tools: Dict[str, ToolRecord] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self._notification_handlers: Dict[str, List[Callable]] = {}
        self._server_id = uuid.uuid4().hex[:8]
        self._started_at = datetime.utcnow().isoformat()

    # ── Tool registration ────────────────────────────────────────

    def register_tool(
        self,
        name: str,
        handler: Callable,
        schema: Optional[Dict] = None,
        required_level: int = 1,
        description: str = "",
    ) -> None:
        """Register a tool handler with the server."""
        self._tools[name] = ToolRecord(
            name=name,
            handler=handler,
            schema=schema,
            required_level=required_level,
            description=description,
        )
        self._circuit_breakers[name] = CircuitBreaker()
        self.permission_engine.register_tool(name, required_level)
        logger.info("MCP: registered tool %s (level=L%d)", name, required_level)

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool."""
        if name not in self._tools:
            return False
        del self._tools[name]
        self._circuit_breakers.pop(name, None)
        return True

    # ── Notification handlers ────────────────────────────────────

    def on_notification(self, method: str, handler: Callable) -> None:
        """Register a handler for a JSON-RPC notification method."""
        if method not in self._notification_handlers:
            self._notification_handlers[method] = []
        self._notification_handlers[method].append(handler)

    # ── Request handling ─────────────────────────────────────────

    async def handle_request(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Route a single JSON-RPC request to the appropriate handler."""
        method = request.method

        if method == "ping":
            return make_success_response(request.id, {
                "pong": True,
                "server_id": self._server_id,
                "started_at": self._started_at,
            })

        elif method == "tools/list":
            return self._handle_tools_list(request)

        elif method == "tools/describe":
            return self._handle_tools_describe(request)

        elif method == "tools/call":
            return await self._handle_tool_call(request)

        else:
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.METHOD_NOT_FOUND,
                f"Method not found: {method}",
            )

    async def handle_notification(self, notification: JSONRPCNotification) -> None:
        """Handle a JSON-RPC notification (no response expected)."""
        handlers = self._notification_handlers.get(notification.method, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(notification.params)
                else:
                    handler(notification.params)
            except Exception as exc:
                logger.error("Notification handler error for %s: %s", notification.method, exc)

    async def handle_raw(self, data: bytes) -> Optional[bytes]:
        """Parse and handle raw bytes, returning response bytes.

        Returns None for notifications (which require no response).
        Supports single requests and batch requests.
        """
        # Try batch first
        batch = parse_batch_request(data)
        if batch and batch.requests:
            return (await self._handle_batch(batch)).serialize()

        # Try single message
        message = parse_message(data)
        if isinstance(message, JSONRPCRequest):
            response = await self.handle_request(message)
            return response.serialize()
        elif isinstance(message, JSONRPCNotification):
            await self.handle_notification(message)
            return None

        # Parse error
        return make_error_response(
            "",
            JSONRPCErrorCodes.PARSE_ERROR,
            "Failed to parse request",
        ).serialize()

    # ── Method handlers ──────────────────────────────────────────

    def _handle_tools_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle ``tools/list``."""
        tools = []
        for name, rec in self._tools.items():
            cb = self._circuit_breakers.get(name)
            tools.append({
                "name": name,
                "description": rec.description,
                "required_level": rec.required_level,
                "circuit_breaker": cb.state if cb else "unknown",
            })
        return make_success_response(request.id, {"tools": tools, "count": len(tools)})

    def _handle_tools_describe(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle ``tools/describe``."""
        tool_name = request.params.get("name", "")
        if tool_name not in self._tools:
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.METHOD_NOT_FOUND,
                f"Tool not found: {tool_name}",
            )
        rec = self._tools[tool_name]
        return make_success_response(request.id, {
            "name": rec.name,
            "schema": rec.schema,
            "required_level": rec.required_level,
            "description": rec.description,
        })

    async def _handle_tool_call(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle ``tools/call`` with full safety pipeline."""
        tool_name = request.params.get("name", "")
        arguments = request.params.get("arguments", {})
        context = request.params.get("context", {})
        agent_id = context.get("agent_id", "")
        autonomy_level = context.get("autonomy_level", 0)

        # 1. Tool exists?
        if tool_name not in self._tools:
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.METHOD_NOT_FOUND,
                f"Tool not found: {tool_name}",
            )

        # 2. Permission check
        perm = self.permission_engine.check_permission(tool_name, autonomy_level, agent_id)
        if not perm.granted:
            self._audit({
                "action": "tool_denied",
                "tool": tool_name,
                "agent": agent_id,
                "reason": perm.reason,
            })
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.PERMISSION_DENIED,
                perm.reason,
                {
                    "tool": tool_name,
                    "required_level": self.permission_engine.get_tool_level(tool_name),
                    "current_level": autonomy_level,
                },
            )

        # 3. Rate limit
        if not self.rate_limiter.allow(agent_id):
            self._audit({"action": "rate_limited", "tool": tool_name, "agent": agent_id})
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.RATE_LIMITED,
                "Rate limited",
                {"retry_after": 60},
            )

        if not self.rate_limiter.allow_agent(agent_id):
            remaining = self.rate_limiter.agent_remaining(agent_id)
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.RATE_LIMITED,
                "Agent rate limit exceeded",
                {"remaining": remaining},
            )

        # 4. Circuit breaker
        cb = self._circuit_breakers.get(tool_name)
        if cb and not cb.can_execute():
            self._audit({"action": "circuit_open", "tool": tool_name, "agent": agent_id})
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.TOOL_UNAVAILABLE,
                f"Tool {tool_name} unavailable (circuit breaker {cb.state})",
            )

        # 5. Execute
        start = time.monotonic()
        try:
            handler = self._tools[tool_name].handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(arguments, context)
            else:
                result = handler(arguments, context)

            if cb:
                cb.record_success()

            duration = (time.monotonic() - start) * 1000
            self._audit({
                "action": "tool_call",
                "tool": tool_name,
                "agent": agent_id,
                "status": "success",
                "duration_ms": round(duration, 2),
            })

            return make_success_response(request.id, result)

        except asyncio.TimeoutError:
            if cb:
                cb.record_failure()
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.TIMEOUT,
                f"Tool {tool_name} timed out",
            )

        except Exception as exc:
            if cb:
                cb.record_failure()
            duration = (time.monotonic() - start) * 1000
            self._audit({
                "action": "tool_call",
                "tool": tool_name,
                "agent": agent_id,
                "status": "error",
                "error": str(exc),
                "duration_ms": round(duration, 2),
            })
            return make_error_response(
                request.id,
                JSONRPCErrorCodes.INTERNAL_ERROR,
                str(exc),
            )

    # ── Batch handling ───────────────────────────────────────────

    async def _handle_batch(self, batch: JSONRPCBatchRequest) -> JSONRPCBatchResponse:
        """Handle a batch of requests concurrently."""
        tasks = [self.handle_request(req) for req in batch.requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        result = JSONRPCBatchResponse()
        for resp in responses:
            if isinstance(resp, JSONRPCResponse):
                result.add(resp)
            elif isinstance(resp, Exception):
                result.add(make_error_response(
                    "",
                    JSONRPCErrorCodes.INTERNAL_ERROR,
                    str(resp),
                ))
        return result

    # ── Audit ────────────────────────────────────────────────────

    def _audit(self, entry: Dict[str, Any]) -> None:
        entry["audit_id"] = uuid.uuid4().hex[:12]
        entry["timestamp"] = datetime.utcnow().isoformat()
        entry["server_id"] = self._server_id
        self._audit_log.append(entry)

    def get_audit_log(self, limit: int = 100, tool: Optional[str] = None) -> List[Dict]:
        log = self._audit_log
        if tool:
            log = [e for e in log if e.get("tool") == tool]
        return log[-limit:]

    # ── Properties ───────────────────────────────────────────────

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    @property
    def server_id(self) -> str:
        return self._server_id

    def get_stats(self) -> Dict[str, Any]:
        return {
            "server_id": self._server_id,
            "started_at": self._started_at,
            "tool_count": len(self._tools),
            "audit_entries": len(self._audit_log),
            "circuit_breakers": {
                name: cb.to_dict() for name, cb in self._circuit_breakers.items()
            },
        }
