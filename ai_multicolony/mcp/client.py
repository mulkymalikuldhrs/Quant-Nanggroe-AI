"""MCPClient – JSON-RPC 2.0 client with connection management, tool
discovery, invocation with retries, circuit breaking, and request
timeout handling.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from .protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCErrorCodes,
    make_notification,
)
from .server import MCPServer, CircuitBreaker

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Client: connect to an MCP server, discover tools, and invoke
    them with automatic retries, circuit breaking, and timeout handling.

    The client can operate in two modes:
      1. **Direct** – holds a reference to an :class:`MCPServer` instance
         (in-process communication).
      2. **Remote** – communicates over a transport (HTTP, WebSocket, stdio).
         Provide a ``transport`` callable that accepts :class:`JSONRPCRequest`
         and returns :class:`JSONRPCResponse`.

    Usage (direct)
    --------------
    >>> server = MCPServer()
    >>> client = MCPClient(server=server, agent_id="agent-1", autonomy_level=2)
    >>> tools = await client.list_tools()
    >>> result = await client.call_tool("shell.execute", {"command": "ls"})
    """

    def __init__(
        self,
        server: Optional[MCPServer] = None,
        transport: Optional[Callable] = None,
        agent_id: str = "",
        autonomy_level: int = 1,
        colony_id: str = "",
        max_retries: int = 3,
        default_timeout: float = 30.0,
    ) -> None:
        self._server = server
        self._transport = transport
        self.agent_id = agent_id
        self.autonomy_level = autonomy_level
        self.colony_id = colony_id
        self.max_retries = max_retries
        self.default_timeout = default_timeout

        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._call_history: List[Dict[str, Any]] = []
        self._discovered_tools: List[str] = []
        self._connected = server is not None or transport is not None
        self._client_id = uuid.uuid4().hex[:8]

    # ── Connection management ────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self, server: Optional[MCPServer] = None, transport: Optional[Callable] = None) -> None:
        """Connect to a server or transport."""
        if server:
            self._server = server
        if transport:
            self._transport = transport
        self._connected = True
        # Discover tools on connect
        try:
            await self.list_tools()
        except Exception:
            logger.exception("unhandled_error")
            pass
        logger.info("MCPClient %s connected", self._client_id)

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        self._server = None
        self._transport = None
        self._connected = False
        logger.info("MCPClient %s disconnected", self._client_id)

    # ── Internal send ────────────────────────────────────────────

    async def _send(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Send a request through the server or transport."""
        if self._server:
            return await self._server.handle_request(request)
        if self._transport:
            if asyncio.iscoroutinefunction(self._transport):
                return await self._transport(request)
            return self._transport(request)
        from ..exceptions import MCPError
        raise MCPError("No MCP server or transport connected")

    # ── Tool discovery ───────────────────────────────────────────

    async def list_tools(self) -> List[str]:
        """List available tools on the server."""
        request = JSONRPCRequest(method="tools/list")
        response = await self._send(request)

        if response.is_success() and response.result:
            tools_data = response.result.get("data", {})
            self._discovered_tools = [t["name"] if isinstance(t, dict) else t for t in tools_data.get("tools", [])]
        else:
            self._discovered_tools = []

        return self._discovered_tools

    async def describe_tool(self, name: str) -> Dict[str, Any]:
        """Get the schema and metadata for a specific tool."""
        request = JSONRPCRequest(method="tools/describe", params={"name": name})
        response = await self._send(request)

        if response.is_success() and response.result:
            return response.result.get("data", {})
        if response.error:
            return {"error": response.error.get("message", "Unknown error")}
        return {}

    # ── Tool invocation ──────────────────────────────────────────

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Invoke a tool through the MCP with retries and circuit breaker.

        Parameters
        ----------
        tool_name : str
            Registered tool name.
        arguments : dict
            Arguments matching the tool's input schema.
        timeout : float, optional
            Per-attempt timeout in seconds.
        context : dict, optional
            Additional context; defaults to the client's agent_id
            and autonomy_level.

        Returns
        -------
        dict
            The tool result payload.
        """
        # Circuit breaker check
        cb = self._circuit_breakers.setdefault(tool_name, CircuitBreaker())
        if not cb.can_execute():
            from ..exceptions import ToolUnavailableError
            raise ToolUnavailableError(tool_name)

        # Build context
        ctx = context or {}
        ctx.setdefault("agent_id", self.agent_id)
        ctx.setdefault("autonomy_level", self.autonomy_level)
        ctx.setdefault("colony_id", self.colony_id)

        request = JSONRPCRequest(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments,
                "context": ctx,
            },
        )

        effective_timeout = timeout or self.default_timeout
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self._send(request),
                    timeout=effective_timeout,
                )

                # Success
                if response.is_success() and response.result:
                    cb.record_success()
                    data = response.result.get("data", response.result)
                    self._call_history.append({
                        "tool": tool_name,
                        "status": "success",
                        "attempt": attempt,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    return data if isinstance(data, dict) else {"result": data}

                # Error response
                if response.error:
                    code = response.error.get("code", 0)
                    message = response.error.get("message", "Unknown error")

                    # Rate limited → exponential backoff
                    if code == JSONRPCErrorCodes.RATE_LIMITED:
                        retry_data = response.error.get("data", {})
                        backoff = retry_data.get("retry_after", 2 ** attempt)
                        logger.warning("Rate limited on %s, backing off %.1fs", tool_name, backoff)
                        await asyncio.sleep(backoff)
                        continue

                    # Permission denied → no retry
                    if code == JSONRPCErrorCodes.PERMISSION_DENIED:
                        from ..exceptions import ToolPermissionError
                        required = response.error.get("data", {}).get("required_level", 0)
                        raise ToolPermissionError(tool_name, required, self.autonomy_level)

                    # Tool unavailable → circuit breaker
                    if code == JSONRPCErrorCodes.TOOL_UNAVAILABLE:
                        cb.record_failure()
                        from ..exceptions import ToolUnavailableError
                        raise ToolUnavailableError(tool_name)

                    # Other errors
                    from ..exceptions import ToolError
                    raise ToolError(message)

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Tool {tool_name} timed out after {effective_timeout}s")
                cb.record_failure()
                logger.warning("Timeout on %s attempt %d/%d", tool_name, attempt + 1, self.max_retries)

            except (TimeoutError, Exception) as exc:
                if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
                    pass  # already handled
                else:
                    from ..exceptions import ToolError, MCPError
                    if isinstance(exc, (ToolError, MCPError)):
                        raise
                    last_error = exc
                    cb.record_failure()

                # Exponential backoff before retry
                if attempt < self.max_retries - 1:
                    backoff = 0.5 * (2 ** attempt)
                    logger.info("Retrying %s in %.1fs (attempt %d/%d)", tool_name, backoff, attempt + 2, self.max_retries)
                    await asyncio.sleep(backoff)

        # All retries exhausted
        self._call_history.append({
            "tool": tool_name,
            "status": "failed",
            "attempts": self.max_retries,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        from ..exceptions import ToolError
        raise last_error or ToolError(f"Tool {tool_name} failed after {self.max_retries} retries")

    # ── Ping ─────────────────────────────────────────────────────

    async def ping(self) -> Dict[str, Any]:
        """Ping the server."""
        request = JSONRPCRequest(method="ping")
        try:
            response = await self._send(request)
            if response.is_success() and response.result:
                return response.result.get("data", {})
            return {"pong": False}
        except Exception:
            logger.exception("unhandled_error")
            return {"pong": False}

    # ── Notification ─────────────────────────────────────────────

    async def send_notification(self, method: str, params: Optional[Dict] = None) -> None:
        """Send a notification (no response expected)."""
        if self._server:
            notification = make_notification(method, params)
            await self._server.handle_notification(notification)

    # ── Properties ───────────────────────────────────────────────

    @property
    def call_history(self) -> List[Dict[str, Any]]:
        return list(self._call_history)

    @property
    def discovered_tools(self) -> List[str]:
        return list(self._discovered_tools)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "client_id": self._client_id,
            "agent_id": self.agent_id,
            "autonomy_level": self.autonomy_level,
            "connected": self._connected,
            "discovered_tools": len(self._discovered_tools),
            "total_calls": len(self._call_history),
            "circuit_breakers": {
                name: cb.to_dict() for name, cb in self._circuit_breakers.items()
            },
        }

    def reset_circuit_breaker(self, tool_name: str) -> None:
        """Force-reset the circuit breaker for a tool."""
        cb = self._circuit_breakers.get(tool_name)
        if cb:
            cb.reset()
