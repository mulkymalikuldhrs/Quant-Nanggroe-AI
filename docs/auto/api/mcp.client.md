# mcp.client

## Class: 

State of a client-server connection.

*Line: 55*

---

## Class: 

Represents a connection to an MCP server.

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

**Methods:** is_connected, health_score

*Line: 66*

---

## Class: 

MCP Client for connecting to multiple MCP servers.

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

**Methods:** __init__, connections, client_name, client_version, get_connection, get_connected_servers, get_all_tools, get_status, _get_connection

*Line: 113*

---

## Class: 

MCP Client that connects directly to a local MCPServer instance.

Bypasses HTTP transport for direct in-process communication.
Useful for testing and single-process deployments.

Usage:
    server = MCPServer()
    client = LocalMCPClient(server)
    result = client.call_tool("market_data.get_ticker", {"symbol": "BTC/USDT"})

**Methods:** __init__, initialize, list_tools, call_tool, health_check, find_tool

*Line: 742*

---

## Function: 

Whether the connection is active.

*Line: 98*

---

## Function: 

Connection health score (0.0-1.0) based on error rate.

*Line: 103*

---

## Function: 

Initialize the MCP client.

Args:
    client_name: Client name sent during initialization.
    client_version: Client version sent during initialization.
    default_timeout: Default request timeout in seconds.

*Line: 131*

---

## Function: 

Active server connections.

*Line: 157*

---

## Function: 

Client name.

*Line: 162*

---

## Function: 

Client version.

*Line: 167*

---

## Function: 

Get a server connection by name.

Args:
    name: Connection name.

Returns:
    ServerConnection if found, None otherwise.

*Line: 561*

---

## Function: 

Get names of all connected servers.

Returns:
    List of connected server names.

*Line: 572*

---

## Function: 

Get all tools from all connected servers.

Returns:
    Dict mapping server names to their tool definitions.

*Line: 584*

---

## Function: 

Get client status summary.

Returns:
    Dict with connection details and statistics.

*Line: 596*

---

## Function: 

Get a connection or raise ValueError.

Args:
    name: Connection name.

Returns:
    ServerConnection instance.

Raises:
    ValueError: If the connection does not exist.

*Line: 625*

---

## Function: 

Initialize the local MCP client.

Args:
    server: MCPServer instance to connect to.

*Line: 754*

---

## Function: 

Initialize the connection to the local server.

Returns:
    InitializeResult with server capabilities.

*Line: 764*

---

## Function: 

List all tools from the local server.

Returns:
    List of ToolDefinition objects.

*Line: 789*

---

## Function: 

Call a tool on the local server.

Args:
    tool_name: Tool name to invoke.
    arguments: Tool arguments.

Returns:
    CallToolResult with the execution result.

*Line: 804*

---

## Function: 

Check the health of the local server.

Returns:
    HealthCheckResult with server health status.

*Line: 866*

---

## Function: 

Find a tool by name on the local server.

Args:
    tool_name: Tool name to search for.

Returns:
    ToolDefinition if found, None otherwise.

*Line: 879*

---

