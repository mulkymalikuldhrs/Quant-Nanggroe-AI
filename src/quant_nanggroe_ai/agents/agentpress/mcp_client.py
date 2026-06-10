"""
MCP Client - Model Context Protocol client for AgentPress.

Adapted from suna's MCP system for Quant-Nanggroe-AI.
Provides a standalone MCP client that can:
- Connect to MCP servers via SSE, HTTP, or stdio transports
- Discover available tools from connected servers
- Execute tools on MCP servers with proper error handling
- Cache schemas for performance
- Support multiple concurrent MCP server connections

The MCP protocol allows agents to access external tools and data sources
through a standardized interface, enabling integration with services like
financial data APIs, market data feeds, and trading platforms.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from quant_nanggroe_ai.agents.agentpress.tool import ToolResult

logger = logging.getLogger(__name__)


class MCPTransport(str, Enum):
    """Supported MCP transport types."""
    SSE = "sse"
    HTTP = "http"
    STDIO = "stdio"


class MCPConnectionStatus(str, Enum):
    """Status of an MCP server connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection.

    Attributes:
        name: Human-readable server name
        transport: Transport type (sse, http, stdio)
        url: URL for SSE/HTTP transports
        command: Command for stdio transport
        args: Arguments for stdio transport
        env: Environment variables for stdio transport
        headers: HTTP headers for SSE/HTTP transports
        enabled_tools: Optional list of specific tools to enable
        description: Server description
    """
    name: str
    transport: MCPTransport = MCPTransport.HTTP
    url: Optional[str] = None
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    enabled_tools: Optional[List[str]] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "transport": self.transport.value,
            "url": self.url,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "headers": self.headers,
            "enabled_tools": self.enabled_tools,
            "description": self.description,
        }


@dataclass
class MCPToolSchema:
    """Schema for an MCP tool discovered from a server.

    Attributes:
        name: Tool function name
        description: Tool description
        parameters: JSON Schema for tool parameters
        server_name: Name of the MCP server providing this tool
    """
    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=lambda: {
        "type": "object", "properties": {}, "required": []
    })
    server_name: str = ""

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI function calling format.

        Returns:
            OpenAPI-compatible schema dict
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description or f"Execute {self.name}",
                "parameters": self.parameters,
            }
        }


class MCPClient:
    """Standalone MCP client for connecting to MCP servers.

    Adapted from suna's MCPManager + MCPToolWrapper + MCPRegistry for
    Quant-Nanggroe-AI. Provides a clean interface for:
    - Managing connections to multiple MCP servers
    - Discovering tools from connected servers
    - Executing tools on any connected server
    - Caching schemas for performance

    Usage:
        client = MCPClient()
        await client.add_server(MCPServerConfig(
            name="financial-data",
            transport=MCPTransport.HTTP,
            url="http://mcp-server:8080"
        ))
        tools = await client.discover_tools("financial-data")
        result = await client.execute_tool("get_stock_price", {"symbol": "AAPL"})
    """

    def __init__(self, schema_cache_ttl: int = 3600):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._connections: Dict[str, MCPConnectionStatus] = {}
        self._tool_schemas: Dict[str, MCPToolSchema] = {}
        self._tool_to_server: Dict[str, str] = {}
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._schema_cache_ttl = schema_cache_ttl
        self._cache_timestamps: Dict[str, float] = {}

    async def add_server(self, config: MCPServerConfig) -> bool:
        """Add an MCP server configuration.

        Args:
            config: Server configuration

        Returns:
            True if the server was added successfully
        """
        self._servers[config.name] = config
        self._connections[config.name] = MCPConnectionStatus.DISCONNECTED
        logger.info(f"Added MCP server config: {config.name} ({config.transport.value})")
        return True

    async def remove_server(self, name: str) -> bool:
        """Remove an MCP server and its tools.

        Args:
            name: Server name to remove

        Returns:
            True if removed
        """
        if name not in self._servers:
            return False

        # Remove associated tools
        tools_to_remove = [
            tname for tname, sname in self._tool_to_server.items()
            if sname == name
        ]
        for tname in tools_to_remove:
            self._tool_schemas.pop(tname, None)
            self._tool_to_server.pop(tname, None)

        self._servers.pop(name, None)
        self._connections.pop(name, None)
        logger.info(f"Removed MCP server: {name}")
        return True

    async def discover_tools(self, server_name: Optional[str] = None) -> List[MCPToolSchema]:
        """Discover tools from MCP server(s).

        Args:
            server_name: Specific server to discover from, or None for all

        Returns:
            List of discovered MCPToolSchema objects
        """
        if server_name:
            return await self._discover_from_server(server_name)

        all_tools = []
        for name in list(self._servers.keys()):
            try:
                tools = await self._discover_from_server(name)
                all_tools.extend(tools)
            except Exception as e:
                logger.error(f"Failed to discover tools from {name}: {e}")

        return all_tools

    async def _discover_from_server(self, server_name: str) -> List[MCPToolSchema]:
        """Discover tools from a specific MCP server.

        Args:
            server_name: Server name

        Returns:
            List of discovered tool schemas
        """
        config = self._servers.get(server_name)
        if not config:
            logger.warning(f"Server not found: {server_name}")
            return []

        # Check cache
        cache_key = self._get_cache_key(config)
        if self._is_cache_valid(cache_key):
            cached = self._schema_cache.get(cache_key, {})
            tools = []
            for tool_name, tool_data in cached.items():
                schema = MCPToolSchema(
                    name=tool_name,
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("parameters", {}),
                    server_name=server_name,
                )
                tools.append(schema)
                self._tool_schemas[tool_name] = schema
                self._tool_to_server[tool_name] = server_name
            logger.info(f"Loaded {len(tools)} cached schemas from {server_name}")
            return tools

        # Discover from server
        self._connections[server_name] = MCPConnectionStatus.CONNECTING
        schemas = {}

        try:
            if config.transport == MCPTransport.SSE:
                schemas = await self._discover_sse(config)
            elif config.transport == MCPTransport.HTTP:
                schemas = await self._discover_http(config)
            elif config.transport == MCPTransport.STDIO:
                schemas = await self._discover_stdio(config)
            else:
                logger.error(f"Unknown transport: {config.transport}")
                return []
        except Exception as e:
            self._connections[server_name] = MCPConnectionStatus.ERROR
            logger.error(f"Failed to discover from {server_name}: {e}")
            return []

        # Register discovered tools
        tools = []
        for tool_name, tool_schema in schemas.items():
            # Filter by enabled_tools if specified
            if config.enabled_tools and tool_name not in config.enabled_tools:
                continue

            mcp_schema = MCPToolSchema(
                name=tool_name,
                description=tool_schema.get("description", ""),
                parameters=tool_schema.get("parameters", {
                    "type": "object", "properties": {}, "required": []
                }),
                server_name=server_name,
            )
            tools.append(mcp_schema)
            self._tool_schemas[tool_name] = mcp_schema
            self._tool_to_server[tool_name] = server_name

        # Cache results
        self._schema_cache[cache_key] = schemas
        self._cache_timestamps[cache_key] = time.time()
        self._connections[server_name] = MCPConnectionStatus.CONNECTED

        logger.info(f"Discovered {len(tools)} tools from {server_name}")
        return tools

    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> ToolResult:
        """Execute a tool on its MCP server.

        Args:
            tool_name: Name of the tool to execute
            args: Arguments to pass to the tool

        Returns:
            ToolResult with execution output
        """
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            return ToolResult(success=False, output=f"MCP tool '{tool_name}' not found")

        config = self._servers.get(server_name)
        if not config:
            return ToolResult(success=False, output=f"MCP server '{server_name}' not configured")

        start_time = time.time()
        try:
            if config.transport == MCPTransport.SSE:
                result = await self._execute_sse(config, tool_name, args)
            elif config.transport == MCPTransport.HTTP:
                result = await self._execute_http(config, tool_name, args)
            elif config.transport == MCPTransport.STDIO:
                result = await self._execute_stdio(config, tool_name, args)
            else:
                return ToolResult(success=False, output=f"Unsupported transport: {config.transport}")

            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"MCP tool {tool_name} executed in {elapsed:.1f}ms")
            return result

        except Exception as e:
            return ToolResult(success=False, output=f"MCP tool execution error: {str(e)}")

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAPI schemas for all discovered tools.

        Returns:
            List of OpenAPI schema dicts for LLM function calling
        """
        return [schema.to_openapi() for schema in self._tool_schemas.values()]

    def get_available_tools(self) -> List[str]:
        """Get names of all discovered tools."""
        return list(self._tool_schemas.keys())

    def get_server_status(self, name: str) -> MCPConnectionStatus:
        """Get the connection status of a server."""
        return self._connections.get(name, MCPConnectionStatus.DISCONNECTED)

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "servers": len(self._servers),
            "discovered_tools": len(self._tool_schemas),
            "server_status": {
                name: status.value for name, status in self._connections.items()
            },
        }

    # --- Transport-specific discovery methods ---

    async def _discover_sse(self, config: MCPServerConfig) -> Dict[str, Dict[str, Any]]:
        """Discover tools from SSE MCP server."""
        try:
            from mcp.client.sse import sse_client
            from mcp import ClientSession
        except ImportError:
            logger.error("mcp package required: pip install mcp")
            return {}

        schemas = {}
        try:
            async with sse_client(config.url, headers=config.headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = result.tools if hasattr(result, 'tools') else result
                    for tool in tools:
                        schemas[tool.name] = {
                            "description": tool.description or "",
                            "parameters": getattr(tool, 'inputSchema', {
                                "type": "object", "properties": {}, "required": []
                            }),
                        }
        except Exception as e:
            logger.error(f"SSE discovery failed: {e}")
        return schemas

    async def _discover_http(self, config: MCPServerConfig) -> Dict[str, Dict[str, Any]]:
        """Discover tools from HTTP MCP server."""
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from mcp import ClientSession
        except ImportError:
            logger.error("mcp package required: pip install mcp")
            return {}

        schemas = {}
        try:
            async with streamablehttp_client(config.url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = result.tools if hasattr(result, 'tools') else result
                    for tool in tools:
                        schemas[tool.name] = {
                            "description": tool.description or "",
                            "parameters": getattr(tool, 'inputSchema', {
                                "type": "object", "properties": {}, "required": []
                            }),
                        }
        except Exception as e:
            logger.error(f"HTTP discovery failed: {e}")
        return schemas

    async def _discover_stdio(self, config: MCPServerConfig) -> Dict[str, Dict[str, Any]]:
        """Discover tools from stdio MCP server."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            logger.error("mcp package required: pip install mcp")
            return {}

        schemas = {}
        try:
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env,
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = result.tools if hasattr(result, 'tools') else result
                    for tool in tools:
                        schemas[tool.name] = {
                            "description": tool.description or "",
                            "parameters": getattr(tool, 'inputSchema', {
                                "type": "object", "properties": {}, "required": []
                            }),
                        }
        except Exception as e:
            logger.error(f"stdio discovery failed: {e}")
        return schemas

    # --- Transport-specific execution methods ---

    async def _execute_sse(self, config: MCPServerConfig, tool_name: str, args: Dict) -> ToolResult:
        """Execute a tool via SSE transport."""
        try:
            from mcp.client.sse import sse_client
            from mcp import ClientSession
        except ImportError:
            return ToolResult(success=False, output="mcp package not installed")

        try:
            async with sse_client(config.url, headers=config.headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=args)
                    content = result.content if hasattr(result, 'content') else str(result)
                    return ToolResult(success=True, output=str(content))
        except Exception as e:
            return ToolResult(success=False, output=f"SSE execution error: {e}")

    async def _execute_http(self, config: MCPServerConfig, tool_name: str, args: Dict) -> ToolResult:
        """Execute a tool via HTTP transport."""
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from mcp import ClientSession
        except ImportError:
            return ToolResult(success=False, output="mcp package not installed")

        try:
            async with streamablehttp_client(config.url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=args)
                    content = result.content if hasattr(result, 'content') else str(result)
                    return ToolResult(success=True, output=str(content))
        except Exception as e:
            return ToolResult(success=False, output=f"HTTP execution error: {e}")

    async def _execute_stdio(self, config: MCPServerConfig, tool_name: str, args: Dict) -> ToolResult:
        """Execute a tool via stdio transport."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            return ToolResult(success=False, output="mcp package not installed")

        try:
            server_params = StdioServerParameters(
                command=config.command, args=config.args, env=config.env
            )
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments=args)
                    content = result.content if hasattr(result, 'content') else str(result)
                    return ToolResult(success=True, output=str(content))
        except Exception as e:
            return ToolResult(success=False, output=f"stdio execution error: {e}")

    # --- Cache helpers ---

    def _get_cache_key(self, config: MCPServerConfig) -> str:
        config_str = json.dumps(config.to_dict(), sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self._schema_cache:
            return False
        timestamp = self._cache_timestamps.get(cache_key, 0)
        return (time.time() - timestamp) < self._schema_cache_ttl
