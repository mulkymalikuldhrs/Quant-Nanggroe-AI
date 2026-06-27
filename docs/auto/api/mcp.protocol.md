# mcp.protocol

## Class: 

JSON-RPC protocol version.

*Line: 28*

---

## Class: 

MCP-specific and JSON-RPC standard error codes.

Standard JSON-RPC error codes: -32700 to -32603
MCP-specific error codes: -32000 to -32099

*Line: 34*

---

## Class: 

JSON-RPC 2.0 error object.

Attributes:
    code: Error code indicating the type of error.
    message: Human-readable error description.
    data: Optional additional error information.

*Line: 57*

---

## Class: 

JSON-RPC 2.0 request message.

Attributes:
    jsonrpc: Protocol version, always "2.0".
    id: Request identifier for correlation.
    method: Method name to invoke.
    params: Parameters for the method.

*Line: 76*

---

## Class: 

JSON-RPC 2.0 notification (no response expected).

Attributes:
    jsonrpc: Protocol version, always "2.0".
    method: Method name for the notification.
    params: Parameters for the notification.

*Line: 99*

---

## Class: 

JSON-RPC 2.0 success response.

Attributes:
    jsonrpc: Protocol version.
    id: Correlation ID matching the request.
    result: The result of the method invocation.

*Line: 120*

---

## Class: 

JSON-RPC 2.0 error response.

Attributes:
    jsonrpc: Protocol version.
    id: Correlation ID matching the request (null if not parseable).
    error: Error object with details.

*Line: 136*

---

## Class: 

JSON Schema for tool input validation.

Attributes:
    type: Schema type, always "object".
    properties: Property definitions for each input parameter.
    required: List of required property names.
    additional_properties: Whether additional properties are allowed.

*Line: 161*

---

## Class: 

JSON Schema for tool output validation.

Attributes:
    type: Schema type.
    properties: Property definitions for each output field.

*Line: 188*

---

## Class: 

Complete definition of an MCP tool.

Every tool must specify its name, description, input schema, and output schema.
Tools are the primary interface for agent-tool communication in MCP.

Attributes:
    name: Unique tool identifier (e.g., "market_data.get_ohlcv").
    description: Human-readable description of what the tool does.
    input_schema: JSON Schema for validating tool inputs.
    output_schema: JSON Schema for describing tool outputs.
    annotations: Optional metadata annotations.

*Line: 205*

---

## Class: 

Result from a tool execution.

Attributes:
    content: List of content items (text, image, resource).
    is_error: Whether the result represents an error.
    tool_name: Name of the tool that was executed.
    execution_time_ms: Wall-clock execution time in milliseconds.
    metadata: Optional additional metadata.

**Methods:** text_result, error_result, json_result

*Line: 241*

---

## Class: 

Server capability advertisement.

Attributes:
    tools: Whether the server supports tool operations.
    resources: Whether the server supports resource operations.
    prompts: Whether the server supports prompt operations.
    logging: Whether the server supports logging.
    streaming: Whether the server supports SSE streaming.
    version: Protocol version supported.

*Line: 363*

---

## Class: 

Server identity and metadata.

Attributes:
    name: Server name.
    version: Server version.
    description: Human-readable server description.
    capabilities: Server capabilities.

*Line: 383*

---

## Class: 

Parameters for the initialize request.

Attributes:
    client_info: Client identity information.
    capabilities: Client capabilities.
    protocol_version: Protocol version the client supports.

*Line: 405*

---

## Class: 

Result of the initialize request.

Attributes:
    server_info: Server identity and capabilities.
    protocol_version: Negotiated protocol version.
    capabilities: Server capabilities.

*Line: 425*

---

## Class: 

Result of the tools/list request.

Attributes:
    tools: List of available tool definitions.

*Line: 447*

---

## Class: 

Parameters for the tools/call request.

Attributes:
    name: Name of the tool to invoke.
    arguments: Arguments to pass to the tool.

*Line: 459*

---

## Class: 

Result of the tools/call request.

Wraps the ToolCallResult in a standard MCP envelope.

Attributes:
    content: List of content items.
    is_error: Whether the result is an error.
    tool_name: Name of the tool that was executed.
    execution_time_ms: Execution time in milliseconds.
    metadata: Optional additional metadata.

**Methods:** from_tool_call_result

*Line: 473*

---

## Class: 

Result of a health check request.

Attributes:
    status: Health status (healthy, degraded, unhealthy).
    version: Server version.
    uptime_seconds: Server uptime in seconds.
    tools_registered: Number of registered tools.
    active_connections: Number of active connections.
    details: Additional health details.

*Line: 522*

---

## Class: 

Server-Sent Event for streaming tool results.

Attributes:
    event: Event type (progress, result, error).
    data: Event payload.
    id: Optional event ID for replay.

*Line: 557*

---

## Function: 

Create a JSON-RPC 2.0 request.

Args:
    method: Method name.
    params: Optional method parameters.
    request_id: Optional request ID (auto-generated if not provided).

Returns:
    JSONRPCRequest instance.

*Line: 581*

---

## Function: 

Create a JSON-RPC 2.0 success response.

Args:
    request_id: Correlation ID from the request.
    result: Method result.

Returns:
    JSONRPCSuccessResponse instance.

*Line: 603*

---

## Function: 

Create a JSON-RPC 2.0 error response.

Args:
    error_code: Error code from MCPErrorCodes.
    error_message: Human-readable error description.
    request_id: Correlation ID (None if request couldn't be parsed).
    error_data: Optional additional error data.

Returns:
    JSONRPCErrorResponse instance.

*Line: 619*

---

## Function: 

Create a JSON-RPC 2.0 notification.

Args:
    method: Notification method name.
    params: Optional notification parameters.

Returns:
    JSONRPCNotification instance.

*Line: 646*

---

## Function: 

Create a text content result.

Args:
    text: Text content.
    tool_name: Name of the tool that was executed.
    execution_time_ms: Execution time in milliseconds.
    is_error: Whether result is an error.
    metadata: Optional additional metadata.

Returns:
    ToolCallResult with text content.

*Line: 267*

---

## Function: 

Create an error result.

Args:
    error_message: Error description.
    tool_name: Name of the tool that failed.
    execution_time_ms: Execution time before failure.
    error_code: Optional error code.

Returns:
    ToolCallResult representing an error.

*Line: 296*

---

## Function: 

Create a JSON content result.

Args:
    data: JSON-serializable data.
    tool_name: Name of the tool that was executed.
    execution_time_ms: Execution time in milliseconds.
    metadata: Optional additional metadata.

Returns:
    ToolCallResult with JSON content.

*Line: 326*

---

## Function: 

Create from a ToolCallResult.

Args:
    result: ToolCallResult to convert.

Returns:
    CallToolResult instance.

*Line: 501*

---

