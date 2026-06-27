# mcp.server

## Class: 

Abstract base class for MCP tool handlers.

Every tool must implement this interface. The handler provides:
- Tool definition (name, description, schemas)
- Sync and async execution methods
- Input validation via Pydantic models

Usage:
    class MyToolHandler(ToolHandler):
        @property
        def definition(self) -> ToolDefinition:
            return ToolDefinition(...)

        def execute(self, arguments: dict) -> ToolCallResult:
            ...

        async def execute_async(self, arguments: dict) -> ToolCallResult:
            ...

**Methods:** definition, execute, validate_arguments

*Line: 54*

---

## Class: 

Tool handler that wraps a simple function.

Convenience class for registering functions as MCP tools
without creating a full ToolHandler subclass.

Usage:
    handler = FunctionToolHandler(
        name="market_data.get_ticker",
        description="Get current ticker data",
        input_schema=ToolInputSchema(...),
        func=get_ticker_impl,
    )

**Methods:** __init__, definition, execute

*Line: 138*

---

## Class: 

MCP Server for tool registration, discovery, and execution.

Implements the MCP specification for tool communication using
JSON-RPC 2.0. Supports both sync and async tool execution,
SSE streaming for long-running tools, and health checks.

Usage:
    server = MCPServer(name="quant-nanggroe", version="0.2.0")
    server.register_tool(my_tool_handler)
    response = server.handle_request(request)

Attributes:
    name: Server name.
    version: Server version.
    description: Human-readable server description.

**Methods:** __init__, name, version, server_info, tools_registered, register_tool, register_function, unregister_tool, get_tool, handle_request, _handle_initialize, _handle_list_tools, _handle_call_tool, _handle_health, list_tool_names, get_tool_definitions, health_check

*Line: 264*

---

## Function: 

Return the tool definition with name, description, and schemas.

Returns:
    ToolDefinition with complete metadata.

*Line: 77*

---

## Function: 

Execute the tool synchronously.

Args:
    arguments: Validated tool arguments.

Returns:
    ToolCallResult with execution result or error.

*Line: 86*

---

## Function: 

Validate tool arguments against the input schema.

Args:
    arguments: Arguments to validate.

Returns:
    Error message if validation fails, None if valid.

*Line: 111*

---

## Function: 

Initialize the function tool handler.

Args:
    name: Tool name in dot-notation namespace.
    description: Human-readable description.
    input_schema: Input validation schema.
    func: Synchronous implementation function.
    output_schema: Optional output schema.
    annotations: Optional metadata annotations.
    async_func: Optional async implementation function.

*Line: 153*

---

## Function: 

Return the tool definition.

*Line: 183*

---

## Function: 

Execute the wrapped function synchronously.

Args:
    arguments: Tool arguments.

Returns:
    ToolCallResult from the function output.

*Line: 193*

---

## Function: 

Initialize the MCP server.

Args:
    name: Server name.
    version: Server version.
    description: Server description.
    capabilities: Server capabilities (defaults to all enabled).

*Line: 282*

---

## Function: 

Server name.

*Line: 313*

---

## Function: 

Server version.

*Line: 318*

---

## Function: 

Server identity and capabilities.

*Line: 323*

---

## Function: 

Number of registered tools.

*Line: 333*

---

## Function: 

Register a tool handler.

Args:
    handler: ToolHandler instance to register.

Raises:
    ValueError: If a tool with the same name is already registered.

*Line: 339*

---

## Function: 

Register a function as an MCP tool.

Convenience method that wraps a function in a FunctionToolHandler.

Args:
    name: Tool name.
    description: Tool description.
    input_schema: Input validation schema.
    func: Synchronous implementation function.
    output_schema: Optional output schema.
    annotations: Optional metadata annotations.
    async_func: Optional async implementation function.

*Line: 361*

---

## Function: 

Unregister a tool by name.

Args:
    name: Tool name to unregister.

Returns:
    True if the tool was found and removed, False otherwise.

*Line: 395*

---

## Function: 

Get a registered tool handler by name.

Args:
    name: Tool name.

Returns:
    ToolHandler if found, None otherwise.

*Line: 410*

---

## Function: 

Route and handle a JSON-RPC 2.0 request.

Dispatches to the appropriate handler based on the method name.
Supported methods:
- initialize: Server initialization handshake
- tools/list: List available tools
- tools/call: Execute a tool
- health: Health check

Args:
    request: JSON-RPC 2.0 request.

Returns:
    JSON-RPC 2.0 response (success or error).

*Line: 423*

---

## Function: 

Handle the initialize method.

Args:
    request: Initialize request.

Returns:
    Initialize result as a dict.

*Line: 524*

---

## Function: 

Handle the tools/list method.

Args:
    request: List tools request.

Returns:
    ListToolsResult as a dict.

*Line: 552*

---

## Function: 

Handle the tools/call method synchronously.

Args:
    request: Call tool request.

Returns:
    CallToolResult as a dict.

*Line: 569*

---

## Function: 

Handle the health check method.

Args:
    request: Health check request.

Returns:
    HealthCheckResult as a dict.

*Line: 645*

---

## Function: 

List all registered tool names.

Returns:
    Sorted list of tool names.

*Line: 767*

---

## Function: 

Get all tool definitions.

Returns:
    List of ToolDefinition objects.

*Line: 775*

---

## Function: 

Perform a health check.

Returns:
    HealthCheckResult with current server status.

*Line: 783*

---

