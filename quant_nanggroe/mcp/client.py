"""MCP Client for Connecting to External MCP Servers.

Implements a production-grade MCP client that:
- Connects to multiple MCP servers simultaneously
- Discovers tools from each server via the tools/list method
- Executes tools remotely via the tools/call method
- Supports SSE transport for streaming results
- Handles server health monitoring and failover
- Provides a unified tool registry across all connected servers

The client follows the MCP specification for JSON-RPC 2.0 communication
and integrates with the quant_nanggroe type system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx

from quant_nanggroe.mcp.protocol import (
    CallToolParams,
    CallToolResult,
    HealthCheckResult,
    InitializeParams,
    InitializeResult,
    JSONRPCErrorResponse,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCSuccessResponse,
    ListToolsResult,
    MCPErrorCodes,
    ServerCapabilities,
    ServerInfo,
    SSEEvent,
    ToolCallResult,
    ToolDefinition,
    make_error_response,
    make_request,
    make_success_response,
)

logger = logging.getLogger(__name__)


# ─── Connection State ─────────────────────────────────────────────────────────


class ConnectionState(str, Enum):
    """State of a client-server connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class ServerConnection:
    """Represents a connection to an MCP server.

    Attributes:
        name: Connection name/identifier.
        url: Server URL.
        state: Current connection state.
        server_info: Server identity (populated after initialization).
        capabilities: Server capabilities (populated after initialization).
        tools: Tools discovered from this server.
        last_health_check: Timestamp of last health check.
        last_error: Last error message.
        request_count: Number of requests sent.
        error_count: Number of errors encountered.
        headers: HTTP headers for requests.
        timeout: Request timeout in seconds.
    """

    name: str
    url: str
    state: ConnectionState = ConnectionState.DISCONNECTED
    server_info: Optional[ServerInfo] = None
    capabilities: Optional[ServerCapabilities] = None
    tools: List[ToolDefinition] = field(default_factory=list)
    last_health_check: Optional[float] = None
    last_error: Optional[str] = None
    request_count: int = 0
    error_count: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0

    @property
    def is_connected(self) -> bool:
        """Whether the connection is active."""
        return self.state == ConnectionState.CONNECTED

    @property
    def health_score(self) -> float:
        """Connection health score (0.0-1.0) based on error rate."""
        if self.request_count == 0:
            return 1.0
        return 1.0 - (self.error_count / self.request_count)


# ─── MCP Client ───────────────────────────────────────────────────────────────


class MCPClient:
    """MCP Client for connecting to multiple MCP servers.

    Provides a unified interface for discovering and invoking tools
    across multiple MCP server connections.

    Usage:
        client = MCPClient()
        await client.connect("quant-server", "http://localhost:8000/mcp")
        tools = await client.list_tools("quant-server")
        result = await client.call_tool("quant-server", "market_data.get_ticker", {"symbol": "BTC/USDT"})

    Attributes:
        connections: Dict of active server connections.
        client_name: Client name for identification.
        client_version: Client version.
    """

    def __init__(
        self,
        client_name: str = "quant-nanggroe-mcp-client",
        client_version: str = "0.2.0",
        default_timeout: float = 30.0,
    ) -> None:
        """Initialize the MCP client.

        Args:
            client_name: Client name sent during initialization.
            client_version: Client version sent during initialization.
            default_timeout: Default request timeout in seconds.
        """
        self._connections: Dict[str, ServerConnection] = {}
        self._client_name = client_name
        self._client_version = client_version
        self._default_timeout = default_timeout
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(
            "MCP Client initialized: name=%s, version=%s",
            client_name,
            client_version,
        )

    @property
    def connections(self) -> Dict[str, ServerConnection]:
        """Active server connections."""
        return self._connections

    @property
    def client_name(self) -> str:
        """Client name."""
        return self._client_name

    @property
    def client_version(self) -> str:
        """Client version."""
        return self._client_version

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Returns:
            httpx.AsyncClient instance.
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self._default_timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._http_client

    # ─── Connection Management ────────────────────────────────────────────

    async def connect(
        self,
        name: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        auto_discover: bool = True,
    ) -> ServerConnection:
        """Connect to an MCP server and perform initialization handshake.

        Args:
            name: Connection name/identifier.
            url: Server URL.
            headers: Optional HTTP headers.
            timeout: Request timeout in seconds.
            auto_discover: Whether to auto-discover tools after connecting.

        Returns:
            ServerConnection with connection state.

        Raises:
            ConnectionError: If the connection or initialization fails.
        """
        connection = ServerConnection(
            name=name,
            url=url,
            headers=headers or {},
            timeout=timeout or self._default_timeout,
        )
        connection.state = ConnectionState.CONNECTING
        self._connections[name] = connection

        try:
            # Step 1: Initialize handshake
            connection.state = ConnectionState.INITIALIZING
            init_result = await self._send_initialize(connection)

            connection.server_info = init_result.server_info
            connection.capabilities = init_result.capabilities
            connection.state = ConnectionState.CONNECTED

            logger.info(
                "Connected to MCP server: name=%s, url=%s, server=%s v%s",
                name,
                url,
                init_result.server_info.name,
                init_result.server_info.version,
            )

            # Step 2: Auto-discover tools
            if auto_discover and connection.capabilities and connection.capabilities.tools:
                await self.discover_tools(name)

            return connection

        except Exception as exc:
            connection.state = ConnectionState.ERROR
            connection.last_error = str(exc)
            logger.error(
                "Failed to connect to MCP server: name=%s, url=%s, error=%s",
                name,
                url,
                exc,
            )
            raise ConnectionError(
                f"Failed to connect to {name} at {url}: {exc}"
            ) from exc

    async def disconnect(self, name: str) -> bool:
        """Disconnect from an MCP server.

        Args:
            name: Connection name.

        Returns:
            True if disconnected successfully.
        """
        connection = self._connections.get(name)
        if connection is None:
            return False

        connection.state = ConnectionState.DISCONNECTED
        connection.tools = []
        logger.info("Disconnected from MCP server: name=%s", name)
        return True

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for name in list(self._connections.keys()):
            await self.disconnect(name)

    async def close(self) -> None:
        """Close the client and all connections."""
        await self.disconnect_all()
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    # ─── Tool Discovery ──────────────────────────────────────────────────

    async def discover_tools(self, name: str) -> List[ToolDefinition]:
        """Discover tools from a connected MCP server.

        Args:
            name: Connection name.

        Returns:
            List of ToolDefinition objects discovered from the server.

        Raises:
            ValueError: If the connection does not exist or is not connected.
        """
        connection = self._get_connection(name)
        if not connection.is_connected:
            raise ValueError(f"Connection {name!r} is not connected")

        request = make_request("tools/list")
        response = await self._send_request(connection, request)

        if isinstance(response, JSONRPCSuccessResponse):
            result = ListToolsResult(**response.result)
            connection.tools = result.tools
            logger.info(
                "Discovered %d tools from %s: %s",
                len(result.tools),
                name,
                [t.name for t in result.tools],
            )
            return result.tools
        else:
            error = response.error if isinstance(response, JSONRPCErrorResponse) else None
            msg = error.message if error else "Unknown error"
            logger.error("Failed to discover tools from %s: %s", name, msg)
            return []

    async def list_tools(
        self, name: Optional[str] = None
    ) -> Dict[str, List[ToolDefinition]]:
        """List tools from one or all connected servers.

        Args:
            name: Optional connection name. If None, lists from all servers.

        Returns:
            Dict mapping server names to their tool lists.
        """
        if name:
            connection = self._get_connection(name)
            return {name: connection.tools}

        return {
            conn_name: conn.tools
            for conn_name, conn in self._connections.items()
            if conn.is_connected
        }

    async def find_tool(
        self, tool_name: str
    ) -> Optional[Tuple[str, ToolDefinition]]:
        """Find which server provides a specific tool.

        Args:
            tool_name: Tool name to search for.

        Returns:
            Tuple of (server_name, ToolDefinition) if found, None otherwise.
        """
        for conn_name, connection in self._connections.items():
            if not connection.is_connected:
                continue
            for tool in connection.tools:
                if tool.name == tool_name:
                    return (conn_name, tool)
        return None

    # ─── Tool Execution ──────────────────────────────────────────────────

    async def call_tool(
        self,
        name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> CallToolResult:
        """Call a tool on a specific MCP server.

        Args:
            name: Connection name.
            tool_name: Tool name to invoke.
            arguments: Tool arguments.

        Returns:
            CallToolResult with the tool execution result.

        Raises:
            ValueError: If the connection does not exist or is not connected.
        """
        connection = self._get_connection(name)
        if not connection.is_connected:
            raise ValueError(f"Connection {name!r} is not connected")

        call_params = CallToolParams(name=tool_name, arguments=arguments)
        request = make_request(
            method="tools/call",
            params=call_params.model_dump(),
        )

        response = await self._send_request(connection, request)

        if isinstance(response, JSONRPCSuccessResponse):
            return CallToolResult(**response.result)
        else:
            error = response.error if isinstance(response, JSONRPCErrorResponse) else None
            error_msg = error.message if error else "Unknown error"
            error_code = error.code if error else MCPErrorCodes.INTERNAL_ERROR

            return CallToolResult(
                content=[{"type": "text", "text": f"Error: {error_msg}"}],
                is_error=True,
                tool_name=tool_name,
                metadata={"error_code": error_code},
            )

    async def call_tool_auto(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> CallToolResult:
        """Call a tool, automatically routing to the correct server.

        Searches all connected servers for the tool and invokes it
        on the first server that provides it.

        Args:
            tool_name: Tool name to invoke.
            arguments: Tool arguments.

        Returns:
            CallToolResult with the tool execution result.

        Raises:
            ValueError: If no server provides the requested tool.
        """
        result = await self.find_tool(tool_name)
        if result is None:
            return CallToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Error: Tool {tool_name!r} not found on any connected server",
                    }
                ],
                is_error=True,
                tool_name=tool_name,
                metadata={"error_code": MCPErrorCodes.UNKNOWN_TOOL},
            )

        server_name, _ = result
        return await self.call_tool(server_name, tool_name, arguments)

    # ─── SSE Streaming ───────────────────────────────────────────────────

    async def stream_tool(
        self,
        name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> AsyncIterator[SSEEvent]:
        """Stream tool execution results via SSE.

        Args:
            name: Connection name.
            tool_name: Tool name to invoke.
            arguments: Tool arguments.

        Yields:
            SSEEvent objects for progress updates and final result.
        """
        connection = self._get_connection(name)
        if not connection.is_connected:
            yield SSEEvent(
                event="error",
                data={"message": f"Connection {name!r} is not connected"},
            )
            return

        client = await self._get_http_client()
        sse_url = f"{connection.url}/sse"

        try:
            async with client.stream(
                "POST",
                sse_url,
                json={
                    "tool_name": tool_name,
                    "arguments": arguments,
                },
                headers=connection.headers,
                timeout=connection.timeout,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue

                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            data = {"raw": data_str}

                        yield SSEEvent(event=event_type, data=data)

        except Exception as exc:
            logger.exception("SSE stream failed for %s/%s", name, tool_name)
            yield SSEEvent(
                event="error",
                data={"message": str(exc), "tool_name": tool_name},
            )

    # ─── Health Check ────────────────────────────────────────────────────

    async def health_check(self, name: str) -> HealthCheckResult:
        """Check the health of a connected MCP server.

        Args:
            name: Connection name.

        Returns:
            HealthCheckResult with server health status.
        """
        connection = self._get_connection(name)

        request = make_request("health")
        response = await self._send_request(connection, request)

        if isinstance(response, JSONRPCSuccessResponse):
            result = HealthCheckResult(**response.result)
            connection.last_health_check = time.monotonic()
            return result
        else:
            return HealthCheckResult(
                status="unhealthy",
                details={"error": "Health check request failed"},
            )

    async def health_check_all(self) -> Dict[str, HealthCheckResult]:
        """Check the health of all connected MCP servers.

        Returns:
            Dict mapping server names to their health check results.
        """
        results: Dict[str, HealthCheckResult] = {}
        for name, connection in self._connections.items():
            if connection.is_connected:
                try:
                    results[name] = await self.health_check(name)
                except Exception as exc:
                    results[name] = HealthCheckResult(
                        status="unhealthy",
                        details={"error": str(exc)},
                    )
            else:
                results[name] = HealthCheckResult(
                    status="unhealthy",
                    details={"error": f"Connection state: {connection.state.value}"},
                )
        return results

    # ─── Utility ──────────────────────────────────────────────────────────

    def get_connection(self, name: str) -> Optional[ServerConnection]:
        """Get a server connection by name.

        Args:
            name: Connection name.

        Returns:
            ServerConnection if found, None otherwise.
        """
        return self._connections.get(name)

    def get_connected_servers(self) -> List[str]:
        """Get names of all connected servers.

        Returns:
            List of connected server names.
        """
        return [
            name
            for name, conn in self._connections.items()
            if conn.is_connected
        ]

    def get_all_tools(self) -> Dict[str, List[ToolDefinition]]:
        """Get all tools from all connected servers.

        Returns:
            Dict mapping server names to their tool definitions.
        """
        return {
            name: conn.tools
            for name, conn in self._connections.items()
            if conn.is_connected
        }

    def get_status(self) -> Dict[str, Any]:
        """Get client status summary.

        Returns:
            Dict with connection details and statistics.
        """
        return {
            "client_name": self._client_name,
            "client_version": self._client_version,
            "connections": {
                name: {
                    "url": conn.url,
                    "state": conn.state.value,
                    "server_info": (
                        conn.server_info.model_dump()
                        if conn.server_info
                        else None
                    ),
                    "tools_count": len(conn.tools),
                    "health_score": conn.health_score,
                    "request_count": conn.request_count,
                    "error_count": conn.error_count,
                }
                for name, conn in self._connections.items()
            },
        }

    # ─── Internal Methods ─────────────────────────────────────────────────

    def _get_connection(self, name: str) -> ServerConnection:
        """Get a connection or raise ValueError.

        Args:
            name: Connection name.

        Returns:
            ServerConnection instance.

        Raises:
            ValueError: If the connection does not exist.
        """
        connection = self._connections.get(name)
        if connection is None:
            raise ValueError(
                f"Connection {name!r} not found. "
                f"Available: {list(self._connections.keys())}"
            )
        return connection

    async def _send_initialize(
        self, connection: ServerConnection
    ) -> InitializeResult:
        """Send initialization request to a server.

        Args:
            connection: Server connection to initialize.

        Returns:
            InitializeResult from the server.
        """
        init_params = InitializeParams(
            client_info={
                "name": self._client_name,
                "version": self._client_version,
            },
            capabilities={"tools": True, "streaming": True},
            protocol_version="2024-11-05",
        )

        request = make_request(
            method="initialize",
            params=init_params.model_dump(),
        )

        response = await self._send_request(connection, request)

        if isinstance(response, JSONRPCSuccessResponse):
            return InitializeResult(**response.result)
        else:
            error = response.error if isinstance(response, JSONRPCErrorResponse) else None
            msg = error.message if error else "Unknown error"
            raise ConnectionError(f"Initialization failed: {msg}")

    async def _send_request(
        self,
        connection: ServerConnection,
        request: JSONRPCRequest,
    ) -> JSONRPCResponse:
        """Send a JSON-RPC request to a server.

        Args:
            connection: Server connection.
            request: JSON-RPC request to send.

        Returns:
            JSON-RPC response (success or error).
        """
        connection.request_count += 1
        client = await self._get_http_client()

        try:
            response = await client.post(
                connection.url,
                json=request.model_dump(),
                headers=connection.headers,
                timeout=connection.timeout,
            )
            response.raise_for_status()

            response_data = response.json()

            # Parse response type
            if "error" in response_data:
                return JSONRPCErrorResponse(**response_data)
            else:
                return JSONRPCSuccessResponse(**response_data)

        except httpx.TimeoutException as exc:
            connection.error_count += 1
            connection.last_error = f"Timeout: {exc}"
            return make_error_response(
                error_code=MCPErrorCodes.INTERNAL_ERROR,
                error_message=f"Request timeout: {exc}",
                request_id=request.id,
            )
        except httpx.HTTPStatusError as exc:
            connection.error_count += 1
            connection.last_error = f"HTTP {exc.response.status_code}"
            return make_error_response(
                error_code=MCPErrorCodes.INTERNAL_ERROR,
                error_message=f"HTTP error {exc.response.status_code}: {exc}",
                request_id=request.id,
            )
        except Exception as exc:
            connection.error_count += 1
            connection.last_error = str(exc)
            return make_error_response(
                error_code=MCPErrorCodes.INTERNAL_ERROR,
                error_message=f"Request failed: {exc}",
                request_id=request.id,
            )


# ─── Local MCP Client (Direct Server Connection) ─────────────────────────────


class LocalMCPClient:
    """MCP Client that connects directly to a local MCPServer instance.

    Bypasses HTTP transport for direct in-process communication.
    Useful for testing and single-process deployments.

    Usage:
        server = MCPServer()
        client = LocalMCPClient(server)
        result = client.call_tool("market_data.get_ticker", {"symbol": "BTC/USDT"})
    """

    def __init__(self, server: Any) -> None:
        """Initialize the local MCP client.

        Args:
            server: MCPServer instance to connect to.
        """
        self._server = server
        self._discovered_tools: List[ToolDefinition] = []
        logger.info("Local MCP Client initialized for server: %s", server.name)

    def initialize(self) -> InitializeResult:
        """Initialize the connection to the local server.

        Returns:
            InitializeResult with server capabilities.
        """
        request = make_request(
            method="initialize",
            params={
                "client_info": {
                    "name": "local-client",
                    "version": "0.2.0",
                },
                "capabilities": {},
                "protocol_version": "2024-11-05",
            },
        )
        response = self._server.handle_request(request)
        if isinstance(response, JSONRPCSuccessResponse):
            return InitializeResult(**response.result)
        else:
            error = response.error if isinstance(response, JSONRPCErrorResponse) else None
            msg = error.message if error else "Unknown error"
            raise ConnectionError(f"Initialization failed: {msg}")

    def list_tools(self) -> List[ToolDefinition]:
        """List all tools from the local server.

        Returns:
            List of ToolDefinition objects.
        """
        request = make_request("tools/list")
        response = self._server.handle_request(request)

        if isinstance(response, JSONRPCSuccessResponse):
            result = ListToolsResult(**response.result)
            self._discovered_tools = result.tools
            return result.tools
        return []

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> CallToolResult:
        """Call a tool on the local server.

        Args:
            tool_name: Tool name to invoke.
            arguments: Tool arguments.

        Returns:
            CallToolResult with the execution result.
        """
        request = make_request(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )
        response = self._server.handle_request(request)

        if isinstance(response, JSONRPCSuccessResponse):
            return CallToolResult(**response.result)
        else:
            error = response.error if isinstance(response, JSONRPCErrorResponse) else None
            error_msg = error.message if error else "Unknown error"
            return CallToolResult(
                content=[{"type": "text", "text": f"Error: {error_msg}"}],
                is_error=True,
                tool_name=tool_name,
            )

    async def call_tool_async(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> CallToolResult:
        """Call a tool on the local server asynchronously.

        Args:
            tool_name: Tool name to invoke.
            arguments: Tool arguments.

        Returns:
            CallToolResult with the execution result.
        """
        request = make_request(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )
        response = await self._server.handle_request_async(request)

        if isinstance(response, JSONRPCSuccessResponse):
            return CallToolResult(**response.result)
        else:
            error = response.error if isinstance(response, JSONRPCErrorResponse) else None
            error_msg = error.message if error else "Unknown error"
            return CallToolResult(
                content=[{"type": "text", "text": f"Error: {error_msg}"}],
                is_error=True,
                tool_name=tool_name,
            )

    def health_check(self) -> HealthCheckResult:
        """Check the health of the local server.

        Returns:
            HealthCheckResult with server health status.
        """
        request = make_request("health")
        response = self._server.handle_request(request)

        if isinstance(response, JSONRPCSuccessResponse):
            return HealthCheckResult(**response.result)
        return HealthCheckResult(status="unhealthy")

    def find_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Find a tool by name on the local server.

        Args:
            tool_name: Tool name to search for.

        Returns:
            ToolDefinition if found, None otherwise.
        """
        for tool in self._discovered_tools:
            if tool.name == tool_name:
                return tool
        return None
