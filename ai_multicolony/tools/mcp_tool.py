"""MCP (Model Context Protocol) tool for external tool integration.

Provides MCP client capabilities to connect to external MCP servers,
discover tools, execute tools, and access resources.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.tool_base import BaseTool
from ai_multicolony.exceptions import ToolExecutionError, MCPError
from ai_multicolony.mcp.client import MCPClient
from ai_multicolony.mcp.protocol import MCPRequest, MCPResponse
from ai_multicolony.types.tools import ToolCall, ToolDefinition, ToolParameter, ToolResult, ToolType

logger = get_logger(__name__)


class MCPTool(BaseTool):
    """MCP protocol tool for external tool integration.

    Features:
    - Connect to and disconnect from MCP servers
    - Tool discovery (list available tools)
    - Tool execution (call tools on MCP servers)
    - Resource access (list and read resources)
    - Server status tracking
    - Graceful fallback when servers are unavailable
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self._servers: dict[str, MCPClient] = {}
        self._server_meta: dict[str, dict[str, Any]] = {}
        self._default_server = self._config.get("default_server", None)

        # Auto-connect to pre-configured servers
        preconfigured = self._config.get("servers", {})
        for name, server_config in preconfigured.items():
            if isinstance(server_config, dict) and "url" in server_config:
                self._servers[name] = MCPClient(
                    server_url=server_config["url"],
                    timeout=server_config.get("timeout", 30.0),
                )
                self._server_meta[name] = {
                    "url": server_config["url"],
                    "connected": False,
                    "tools": [],
                    "resources": [],
                }

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="mcp",
            description=(
                "MCP protocol tool for connecting to and using external "
                "tool servers (tool discovery, execution, resource access)"
            ),
            tool_type=ToolType.MCP,
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description=(
                        "MCP action: connect, disconnect, list_tools, "
                        "call_tool, list_resources, read_resource, status"
                    ),
                    required=True,
                    enum=[
                        "connect", "disconnect", "list_tools",
                        "call_tool", "list_resources", "read_resource", "status",
                    ],
                ),
                ToolParameter(
                    name="server",
                    type="string",
                    description="MCP server name",
                    required=False,
                ),
                ToolParameter(
                    name="url",
                    type="string",
                    description="MCP server URL (for connect action)",
                    required=False,
                ),
                ToolParameter(
                    name="tool_name",
                    type="string",
                    description="Name of the MCP tool to call",
                    required=False,
                ),
                ToolParameter(
                    name="arguments",
                    type="object",
                    description="Arguments for the MCP tool call",
                    required=False,
                ),
                ToolParameter(
                    name="uri",
                    type="string",
                    description="Resource URI (for read_resource action)",
                    required=False,
                ),
            ],
            tags=["mcp", "protocol", "external"],
            requires_permission="mcp.use",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_server(self, server_name: Optional[str]) -> Optional[MCPClient]:
        """Get an MCP client by name.

        Args:
            server_name: The server name, or None for default.

        Returns:
            The MCPClient, or None if not found.
        """
        name = server_name or self._default_server
        if not name:
            return None
        return self._servers.get(name)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute an MCP action."""
        action = tool_call.arguments.get("action", "")

        dispatch = {
            "connect": self._connect,
            "disconnect": self._disconnect,
            "list_tools": self._list_tools,
            "call_tool": self._call_tool,
            "list_resources": self._list_resources,
            "read_resource": self._read_resource,
            "status": self._status,
        }

        handler = dispatch.get(action)
        if handler is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"Unknown MCP action: {action}",
            )
        return await handler(tool_call)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def _connect(self, tool_call: ToolCall) -> ToolResult:
        """Connect to an MCP server."""
        server_name = tool_call.arguments.get("server", "")
        server_url = tool_call.arguments.get("url", "")

        if not server_name:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error="No server name specified",
            )
        if not server_url:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error="No server URL specified",
            )

        client = MCPClient(server_url=server_url)
        self._servers[server_name] = client
        self._server_meta[server_name] = {
            "url": server_url,
            "connected": False,
            "tools": [],
            "resources": [],
        }

        # Try to initialize the connection
        try:
            server_info = await client.initialize()
            self._server_meta[server_name]["connected"] = True
            self._server_meta[server_name]["server_info"] = server_info

            # Auto-discover tools
            try:
                tools = await client.list_tools()
                self._server_meta[server_name]["tools"] = [
                    t.name for t in tools
                ]
            except Exception as e:
                logger.warning("mcp_auto_discover_tools_error", server=server_name, error=str(e))

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=True,
                output=f"Connected to MCP server '{server_name}' at {server_url}\n"
                       f"Server info: {json.dumps(server_info, indent=2)[:500]}",
            )
        except Exception as e:
            # Connection failed but still register for retry
            logger.warning("mcp_connect_error", server=server_name, error=str(e))
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False,
                error=f"Failed to connect to MCP server '{server_name}': {e}",
            )

    async def _disconnect(self, tool_call: ToolCall) -> ToolResult:
        """Disconnect from an MCP server."""
        server_name = tool_call.arguments.get("server", "")
        if server_name in self._servers:
            del self._servers[server_name]
            self._server_meta.pop(server_name, None)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=True, output=f"Disconnected from MCP server: {server_name}",
            )
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="mcp",
            success=False, error=f"MCP server not found: {server_name}",
        )

    async def _list_tools(self, tool_call: ToolCall) -> ToolResult:
        """List available tools on an MCP server."""
        server_name = tool_call.arguments.get("server", self._default_server)

        if not server_name:
            # List all connected servers and their tools
            lines: list[str] = []
            for name, meta in self._server_meta.items():
                tool_names = meta.get("tools", [])
                connected = meta.get("connected", False)
                lines.append(
                    f"  {name} ({meta.get('url', 'N/A')}) "
                    f"[{'connected' if connected else 'disconnected'}]: "
                    f"{', '.join(tool_names) if tool_names else 'no tools discovered'}"
                )
            output = "MCP Servers:\n" + "\n".join(lines) if lines else "No MCP servers configured"
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=True, output=output,
            )

        client = self._get_server(server_name)
        if client is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"MCP server not found: {server_name}",
            )

        try:
            tools = await client.list_tools()
            self._server_meta.setdefault(server_name, {})["tools"] = [t.name for t in tools]

            lines = []
            for t in tools:
                schema_info = ""
                if t.input_schema:
                    props = t.input_schema.get("properties", {})
                    schema_info = f" (params: {', '.join(props.keys())})"
                lines.append(f"  - {t.name}: {t.description}{schema_info}")

            output = f"Tools on '{server_name}':\n" + "\n".join(lines) if lines else "No tools found"
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=True, output=output,
                metadata={"tool_count": len(tools), "tool_names": [t.name for t in tools]},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"Failed to list tools: {e}",
            )

    async def _call_tool(self, tool_call: ToolCall) -> ToolResult:
        """Call a tool on an MCP server."""
        server_name = tool_call.arguments.get("server", self._default_server)
        mcp_tool_name = tool_call.arguments.get("tool_name", "")
        arguments = tool_call.arguments.get("arguments", {})

        if not server_name:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error="No MCP server specified",
            )
        if not mcp_tool_name:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error="No tool name specified",
            )

        client = self._get_server(server_name)
        if client is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"MCP server not found: {server_name}",
            )

        try:
            result = await client.call_tool(mcp_tool_name, arguments)

            output = str(result) if result is not None else "null"
            if isinstance(result, (list, dict)):
                output = json.dumps(result, indent=2, default=str)[:10000]

            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=True, output=output,
                metadata={
                    "server": server_name,
                    "mcp_tool": mcp_tool_name,
                    "result_type": type(result).__name__ if result is not None else "NoneType",
                },
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"MCP tool call failed: {e}",
            )

    async def _list_resources(self, tool_call: ToolCall) -> ToolResult:
        """List available resources on an MCP server."""
        server_name = tool_call.arguments.get("server", self._default_server)
        if not server_name:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error="No MCP server specified",
            )

        client = self._get_server(server_name)
        if client is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"MCP server not found: {server_name}",
            )

        try:
            resources = await client.list_resources()
            self._server_meta.setdefault(server_name, {})["resources"] = [
                r.get("uri", r.get("name", "")) for r in resources
            ]

            lines = []
            for r in resources:
                uri = r.get("uri", "N/A")
                name = r.get("name", "N/A")
                mime = r.get("mimeType", "unknown")
                lines.append(f"  - {name} ({uri}) [{mime}]")

            output = f"Resources on '{server_name}':\n" + "\n".join(lines) if lines else "No resources found"
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=True, output=output,
                metadata={"resource_count": len(resources)},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"Failed to list resources: {e}",
            )

    async def _read_resource(self, tool_call: ToolCall) -> ToolResult:
        """Read a resource from an MCP server."""
        server_name = tool_call.arguments.get("server", self._default_server)
        uri = tool_call.arguments.get("uri", "")

        if not server_name:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error="No MCP server specified",
            )
        if not uri:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error="No resource URI specified",
            )

        client = self._get_server(server_name)
        if client is None:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"MCP server not found: {server_name}",
            )

        try:
            content = await client.read_resource(uri)
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=True, output=content[:50000],
                metadata={"server": server_name, "uri": uri},
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id, tool_name="mcp",
                success=False, error=f"Failed to read resource: {e}",
            )

    async def _status(self, tool_call: ToolCall) -> ToolResult:
        """Get status of all connected MCP servers."""
        lines: list[str] = []
        for name, meta in self._server_meta.items():
            connected = meta.get("connected", False)
            tools = meta.get("tools", [])
            resources = meta.get("resources", [])
            lines.append(
                f"  {name}:\n"
                f"    URL: {meta.get('url', 'N/A')}\n"
                f"    Connected: {connected}\n"
                f"    Tools: {len(tools)} ({', '.join(tools[:5])}{'...' if len(tools) > 5 else ''})\n"
                f"    Resources: {len(resources)}"
            )

        output = "MCP Server Status:\n" + "\n".join(lines) if lines else "No MCP servers configured"
        return ToolResult(
            tool_call_id=tool_call.id, tool_name="mcp",
            success=True, output=output,
            metadata={"server_count": len(self._server_meta)},
        )
