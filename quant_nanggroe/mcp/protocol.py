"""MCP Protocol Types, Messages, and Base Classes.

Implements the Model Context Protocol (MCP) specification using JSON-RPC 2.0
for tool communication. All message types are validated with Pydantic v2.

The MCP protocol enables:
- Tool discovery, listing, and execution
- Health check and capability discovery
- SSE transport for streaming results
- Structured error handling

Reference: https://spec.modelcontextprotocol.io/specification/2024-11-05/
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# ─── JSON-RPC 2.0 Core Types ─────────────────────────────────────────────────


class JSONRPCVersion(str, Enum):
    """JSON-RPC protocol version."""

    V2_0 = "2.0"


class MCPErrorCodes(int, Enum):
    """MCP-specific and JSON-RPC standard error codes.

    Standard JSON-RPC error codes: -32700 to -32603
    MCP-specific error codes: -32000 to -32099
    """

    # JSON-RPC Standard Errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-Specific Errors
    SERVER_NOT_INITIALIZED = -32002
    UNKNOWN_TOOL = -32001
    TOOL_EXECUTION_FAILED = -32003
    RESOURCE_NOT_FOUND = -32004
    RATE_LIMIT_EXCEEDED = -32005
    CAPABILITY_NOT_SUPPORTED = -32006


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object.

    Attributes:
        code: Error code indicating the type of error.
        message: Human-readable error description.
        data: Optional additional error information.
    """

    code: int = Field(..., description="Error code")
    message: str = Field(..., min_length=1, description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")

    model_config = {"from_attributes": True}


# ─── MCP Request Messages ─────────────────────────────────────────────────────


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request message.

    Attributes:
        jsonrpc: Protocol version, always "2.0".
        id: Request identifier for correlation.
        method: Method name to invoke.
        params: Parameters for the method.
    """

    jsonrpc: JSONRPCVersion = JSONRPCVersion.V2_0
    id: Union[str, int] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Request identifier for correlation",
    )
    method: str = Field(..., min_length=1, description="Method name to invoke")
    params: Optional[Dict[str, Any]] = Field(
        None, description="Method parameters"
    )

    model_config = {"from_attributes": True}


class JSONRPCNotification(BaseModel):
    """JSON-RPC 2.0 notification (no response expected).

    Attributes:
        jsonrpc: Protocol version, always "2.0".
        method: Method name for the notification.
        params: Parameters for the notification.
    """

    jsonrpc: JSONRPCVersion = JSONRPCVersion.V2_0
    method: str = Field(..., min_length=1, description="Notification method")
    params: Optional[Dict[str, Any]] = Field(
        None, description="Notification parameters"
    )

    model_config = {"from_attributes": True}


# ─── MCP Response Messages ────────────────────────────────────────────────────


class JSONRPCSuccessResponse(BaseModel):
    """JSON-RPC 2.0 success response.

    Attributes:
        jsonrpc: Protocol version.
        id: Correlation ID matching the request.
        result: The result of the method invocation.
    """

    jsonrpc: JSONRPCVersion = JSONRPCVersion.V2_0
    id: Union[str, int] = Field(..., description="Correlation ID")
    result: Any = Field(..., description="Method result")

    model_config = {"from_attributes": True}


class JSONRPCErrorResponse(BaseModel):
    """JSON-RPC 2.0 error response.

    Attributes:
        jsonrpc: Protocol version.
        id: Correlation ID matching the request (null if not parseable).
        error: Error object with details.
    """

    jsonrpc: JSONRPCVersion = JSONRPCVersion.V2_0
    id: Optional[Union[str, int]] = Field(
        None, description="Correlation ID (null if request could not be parsed)"
    )
    error: JSONRPCError = Field(..., description="Error details")

    model_config = {"from_attributes": True}


# Union type for any JSON-RPC response
JSONRPCResponse = Union[JSONRPCSuccessResponse, JSONRPCErrorResponse]


# ─── MCP Tool Schema ──────────────────────────────────────────────────────────


class ToolInputSchema(BaseModel):
    """JSON Schema for tool input validation.

    Attributes:
        type: Schema type, always "object".
        properties: Property definitions for each input parameter.
        required: List of required property names.
        additional_properties: Whether additional properties are allowed.
    """

    type: str = Field(default="object", description="Schema type")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Property definitions keyed by parameter name",
    )
    required: List[str] = Field(
        default_factory=list,
        description="List of required parameter names",
    )
    additional_properties: bool = Field(
        default=False,
        description="Whether additional properties are allowed",
    )

    model_config = {"from_attributes": True}


class ToolOutputSchema(BaseModel):
    """JSON Schema for tool output validation.

    Attributes:
        type: Schema type.
        properties: Property definitions for each output field.
    """

    type: str = Field(default="object", description="Schema type")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Property definitions keyed by output field name",
    )

    model_config = {"from_attributes": True}


class ToolDefinition(BaseModel):
    """Complete definition of an MCP tool.

    Every tool must specify its name, description, input schema, and output schema.
    Tools are the primary interface for agent-tool communication in MCP.

    Attributes:
        name: Unique tool identifier (e.g., "market_data.get_ohlcv").
        description: Human-readable description of what the tool does.
        input_schema: JSON Schema for validating tool inputs.
        output_schema: JSON Schema for describing tool outputs.
        annotations: Optional metadata annotations.
    """

    name: str = Field(
        ..., min_length=1, pattern=r"^[a-zA-Z][a-zA-Z0-9_\.]*$",
        description="Unique tool identifier in dot-notation namespace",
    )
    description: str = Field(
        ..., min_length=1, description="Human-readable tool description"
    )
    input_schema: ToolInputSchema = Field(
        ..., description="JSON Schema for tool input validation"
    )
    output_schema: ToolOutputSchema = Field(
        default_factory=ToolOutputSchema,
        description="JSON Schema for tool output description",
    )
    annotations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata annotations (e.g., category, version)",
    )

    model_config = {"from_attributes": True}


class ToolCallResult(BaseModel):
    """Result from a tool execution.

    Attributes:
        content: List of content items (text, image, resource).
        is_error: Whether the result represents an error.
        tool_name: Name of the tool that was executed.
        execution_time_ms: Wall-clock execution time in milliseconds.
        metadata: Optional additional metadata.
    """

    content: List[Dict[str, Any]] = Field(
        ..., min_length=1, description="List of content items"
    )
    is_error: bool = Field(default=False, description="Whether result is an error")
    tool_name: str = Field(..., description="Name of the executed tool")
    execution_time_ms: float = Field(
        default=0.0, ge=0, description="Execution time in milliseconds"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {"from_attributes": True}

    @classmethod
    def text_result(
        cls,
        text: str,
        tool_name: str,
        execution_time_ms: float = 0.0,
        is_error: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolCallResult":
        """Create a text content result.

        Args:
            text: Text content.
            tool_name: Name of the tool that was executed.
            execution_time_ms: Execution time in milliseconds.
            is_error: Whether result is an error.
            metadata: Optional additional metadata.

        Returns:
            ToolCallResult with text content.
        """
        return cls(
            content=[{"type": "text", "text": text}],
            is_error=is_error,
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )

    @classmethod
    def error_result(
        cls,
        error_message: str,
        tool_name: str,
        execution_time_ms: float = 0.0,
        error_code: Optional[int] = None,
    ) -> "ToolCallResult":
        """Create an error result.

        Args:
            error_message: Error description.
            tool_name: Name of the tool that failed.
            execution_time_ms: Execution time before failure.
            error_code: Optional error code.

        Returns:
            ToolCallResult representing an error.
        """
        metadata: Dict[str, Any] = {}
        if error_code is not None:
            metadata["error_code"] = error_code
        return cls(
            content=[{"type": "text", "text": f"Error: {error_message}"}],
            is_error=True,
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            metadata=metadata,
        )

    @classmethod
    def json_result(
        cls,
        data: Any,
        tool_name: str,
        execution_time_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "ToolCallResult":
        """Create a JSON content result.

        Args:
            data: JSON-serializable data.
            tool_name: Name of the tool that was executed.
            execution_time_ms: Execution time in milliseconds.
            metadata: Optional additional metadata.

        Returns:
            ToolCallResult with JSON content.
        """
        import json

        return cls(
            content=[
                {
                    "type": "text",
                    "text": json.dumps(data, default=str, indent=2),
                }
            ],
            is_error=False,
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )


# ─── MCP Server Info & Capabilities ───────────────────────────────────────────


class ServerCapabilities(BaseModel):
    """Server capability advertisement.

    Attributes:
        tools: Whether the server supports tool operations.
        resources: Whether the server supports resource operations.
        prompts: Whether the server supports prompt operations.
        logging: Whether the server supports logging.
        streaming: Whether the server supports SSE streaming.
        version: Protocol version supported.
    """

    tools: bool = Field(default=True, description="Tool support")
    resources: bool = Field(default=False, description="Resource support")
    prompts: bool = Field(default=False, description="Prompt support")
    logging: bool = Field(default=True, description="Logging support")
    streaming: bool = Field(default=True, description="SSE streaming support")
    version: str = Field(default="2024-11-05", description="MCP version")


class ServerInfo(BaseModel):
    """Server identity and metadata.

    Attributes:
        name: Server name.
        version: Server version.
        description: Human-readable server description.
        capabilities: Server capabilities.
    """

    name: str = Field(..., min_length=1, description="Server name")
    version: str = Field(..., min_length=1, description="Server version")
    description: str = Field(default="", description="Server description")
    capabilities: ServerCapabilities = Field(
        default_factory=ServerCapabilities,
        description="Server capabilities",
    )


# ─── MCP Lifecycle Messages ───────────────────────────────────────────────────


class InitializeParams(BaseModel):
    """Parameters for the initialize request.

    Attributes:
        client_info: Client identity information.
        capabilities: Client capabilities.
        protocol_version: Protocol version the client supports.
    """

    client_info: Dict[str, str] = Field(
        ..., description="Client identity (name, version)"
    )
    capabilities: Dict[str, Any] = Field(
        default_factory=dict, description="Client capabilities"
    )
    protocol_version: str = Field(
        default="2024-11-05", description="Requested protocol version"
    )


class InitializeResult(BaseModel):
    """Result of the initialize request.

    Attributes:
        server_info: Server identity and capabilities.
        protocol_version: Negotiated protocol version.
        capabilities: Server capabilities.
    """

    server_info: ServerInfo = Field(..., description="Server identity")
    protocol_version: str = Field(
        default="2024-11-05", description="Negotiated protocol version"
    )
    capabilities: ServerCapabilities = Field(
        default_factory=ServerCapabilities,
        description="Server capabilities",
    )


# ─── MCP Tool Operation Messages ──────────────────────────────────────────────


class ListToolsResult(BaseModel):
    """Result of the tools/list request.

    Attributes:
        tools: List of available tool definitions.
    """

    tools: List[ToolDefinition] = Field(
        default_factory=list, description="Available tools"
    )


class CallToolParams(BaseModel):
    """Parameters for the tools/call request.

    Attributes:
        name: Name of the tool to invoke.
        arguments: Arguments to pass to the tool.
    """

    name: str = Field(..., min_length=1, description="Tool name to invoke")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )


class CallToolResult(BaseModel):
    """Result of the tools/call request.

    Wraps the ToolCallResult in a standard MCP envelope.

    Attributes:
        content: List of content items.
        is_error: Whether the result is an error.
        tool_name: Name of the tool that was executed.
        execution_time_ms: Execution time in milliseconds.
        metadata: Optional additional metadata.
    """

    content: List[Dict[str, Any]] = Field(
        ..., description="Result content items"
    )
    is_error: bool = Field(default=False, description="Error flag")
    tool_name: Optional[str] = Field(None, description="Tool name")
    execution_time_ms: Optional[float] = Field(
        None, ge=0, description="Execution time ms"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {"from_attributes": True}

    @classmethod
    def from_tool_call_result(cls, result: ToolCallResult) -> "CallToolResult":
        """Create from a ToolCallResult.

        Args:
            result: ToolCallResult to convert.

        Returns:
            CallToolResult instance.
        """
        return cls(
            content=result.content,
            is_error=result.is_error,
            tool_name=result.tool_name,
            execution_time_ms=result.execution_time_ms,
            metadata=result.metadata,
        )


# ─── MCP Health Check ─────────────────────────────────────────────────────────


class HealthCheckResult(BaseModel):
    """Result of a health check request.

    Attributes:
        status: Health status (healthy, degraded, unhealthy).
        version: Server version.
        uptime_seconds: Server uptime in seconds.
        tools_registered: Number of registered tools.
        active_connections: Number of active connections.
        details: Additional health details.
    """

    status: str = Field(
        default="healthy",
        pattern=r"^(healthy|degraded|unhealthy)$",
        description="Health status",
    )
    version: str = Field(default="0.1.0", description="Server version")
    uptime_seconds: float = Field(
        default=0.0, ge=0, description="Uptime in seconds"
    )
    tools_registered: int = Field(
        default=0, ge=0, description="Number of registered tools"
    )
    active_connections: int = Field(
        default=0, ge=0, description="Active connections count"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional health details"
    )


# ─── MCP SSE Event ────────────────────────────────────────────────────────────


class SSEEvent(BaseModel):
    """Server-Sent Event for streaming tool results.

    Attributes:
        event: Event type (progress, result, error).
        data: Event payload.
        id: Optional event ID for replay.
    """

    event: str = Field(
        ..., pattern=r"^(progress|result|error|ping)$",
        description="Event type",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Event payload"
    )
    id: Optional[str] = Field(None, description="Event ID for replay")

    model_config = {"from_attributes": True}


# ─── Helper Functions ──────────────────────────────────────────────────────────


def make_request(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    request_id: Optional[Union[str, int]] = None,
) -> JSONRPCRequest:
    """Create a JSON-RPC 2.0 request.

    Args:
        method: Method name.
        params: Optional method parameters.
        request_id: Optional request ID (auto-generated if not provided).

    Returns:
        JSONRPCRequest instance.
    """
    return JSONRPCRequest(
        id=request_id or str(uuid.uuid4()),
        method=method,
        params=params,
    )


def make_success_response(
    request_id: Union[str, int],
    result: Any,
) -> JSONRPCSuccessResponse:
    """Create a JSON-RPC 2.0 success response.

    Args:
        request_id: Correlation ID from the request.
        result: Method result.

    Returns:
        JSONRPCSuccessResponse instance.
    """
    return JSONRPCSuccessResponse(id=request_id, result=result)


def make_error_response(
    error_code: int,
    error_message: str,
    request_id: Optional[Union[str, int]] = None,
    error_data: Optional[Any] = None,
) -> JSONRPCErrorResponse:
    """Create a JSON-RPC 2.0 error response.

    Args:
        error_code: Error code from MCPErrorCodes.
        error_message: Human-readable error description.
        request_id: Correlation ID (None if request couldn't be parsed).
        error_data: Optional additional error data.

    Returns:
        JSONRPCErrorResponse instance.
    """
    return JSONRPCErrorResponse(
        id=request_id,
        error=JSONRPCError(
            code=error_code,
            message=error_message,
            data=error_data,
        ),
    )


def make_notification(
    method: str,
    params: Optional[Dict[str, Any]] = None,
) -> JSONRPCNotification:
    """Create a JSON-RPC 2.0 notification.

    Args:
        method: Notification method name.
        params: Optional notification parameters.

    Returns:
        JSONRPCNotification instance.
    """
    return JSONRPCNotification(method=method, params=params)
