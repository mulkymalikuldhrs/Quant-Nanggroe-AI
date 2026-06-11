"""MCP Server Implementation for Tool Registration and Execution.

Implements a production-grade MCP server that:
- Registers trading tools with schema validation
- Handles JSON-RPC 2.0 request routing
- Supports tool discovery, listing, and execution
- Provides SSE transport for streaming results
- Includes health check and capability discovery
- Supports both sync and async tool handlers

The server follows the MCP specification for tool communication
and integrates with the quant_nanggroe_ai type system.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

from quant_nanggroe_ai.mcp.protocol import (
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
    ToolInputSchema,
    ToolOutputSchema,
    make_error_response,
    make_success_response,
)

logger = logging.getLogger(__name__)


# ─── Tool Handler Protocol ────────────────────────────────────────────────────


class ToolHandler(ABC):
    """Abstract base class for MCP tool handlers.

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
    """

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool definition with name, description, and schemas.

        Returns:
            ToolDefinition with complete metadata.
        """
        ...

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> ToolCallResult:
        """Execute the tool synchronously.

        Args:
            arguments: Validated tool arguments.

        Returns:
            ToolCallResult with execution result or error.
        """
        ...

    async def execute_async(self, arguments: Dict[str, Any]) -> ToolCallResult:
        """Execute the tool asynchronously.

        Default implementation wraps the sync execute() in a thread.
        Override for truly async implementations.

        Args:
            arguments: Validated tool arguments.

        Returns:
            ToolCallResult with execution result or error.
        """
        return await asyncio.to_thread(self.execute, arguments)

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate tool arguments against the input schema.

        Args:
            arguments: Arguments to validate.

        Returns:
            Error message if validation fails, None if valid.
        """
        schema = self.definition.input_schema
        required_fields = schema.required

        # Check required fields
        missing = [f for f in required_fields if f not in arguments]
        if missing:
            return f"Missing required arguments: {', '.join(missing)}"

        # Check for unknown fields if additional_properties is False
        if not schema.additional_properties:
            known_fields = set(schema.properties.keys())
            unknown = [f for f in arguments if f not in known_fields]
            if unknown:
                return f"Unknown arguments: {', '.join(unknown)}"

        return None


class FunctionToolHandler(ToolHandler):
    """Tool handler that wraps a simple function.

    Convenience class for registering functions as MCP tools
    without creating a full ToolHandler subclass.

    Usage:
        handler = FunctionToolHandler(
            name="market_data.get_ticker",
            description="Get current ticker data",
            input_schema=ToolInputSchema(...),
            func=get_ticker_impl,
        )
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: ToolInputSchema,
        func: Callable[..., Any],
        output_schema: Optional[ToolOutputSchema] = None,
        annotations: Optional[Dict[str, Any]] = None,
        async_func: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Initialize the function tool handler.

        Args:
            name: Tool name in dot-notation namespace.
            description: Human-readable description.
            input_schema: Input validation schema.
            func: Synchronous implementation function.
            output_schema: Optional output schema.
            annotations: Optional metadata annotations.
            async_func: Optional async implementation function.
        """
        self._name = name
        self._description = description
        self._input_schema = input_schema
        self._func = func
        self._output_schema = output_schema or ToolOutputSchema()
        self._annotations = annotations or {}
        self._async_func = async_func

    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name=self._name,
            description=self._description,
            input_schema=self._input_schema,
            output_schema=self._output_schema,
            annotations=self._annotations,
        )

    def execute(self, arguments: Dict[str, Any]) -> ToolCallResult:
        """Execute the wrapped function synchronously.

        Args:
            arguments: Tool arguments.

        Returns:
            ToolCallResult from the function output.
        """
        start = time.monotonic()
        try:
            result = self._func(**arguments)
            elapsed_ms = (time.monotonic() - start) * 1000

            if isinstance(result, ToolCallResult):
                result.execution_time_ms = elapsed_ms
                return result

            return ToolCallResult.json_result(
                data=result,
                tool_name=self._name,
                execution_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.exception("Tool %s execution failed", self._name)
            return ToolCallResult.error_result(
                error_message=str(exc),
                tool_name=self._name,
                execution_time_ms=elapsed_ms,
            )

    async def execute_async(self, arguments: Dict[str, Any]) -> ToolCallResult:
        """Execute the wrapped function asynchronously.

        Args:
            arguments: Tool arguments.

        Returns:
            ToolCallResult from the function output.
        """
        if self._async_func is not None:
            start = time.monotonic()
            try:
                result = await self._async_func(**arguments)
                elapsed_ms = (time.monotonic() - start) * 1000

                if isinstance(result, ToolCallResult):
                    result.execution_time_ms = elapsed_ms
                    return result

                return ToolCallResult.json_result(
                    data=result,
                    tool_name=self._name,
                    execution_time_ms=elapsed_ms,
                )
            except Exception as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.exception("Async tool %s execution failed", self._name)
                return ToolCallResult.error_result(
                    error_message=str(exc),
                    tool_name=self._name,
                    execution_time_ms=elapsed_ms,
                )

        return await asyncio.to_thread(self.execute, arguments)


# ─── MCP Server ───────────────────────────────────────────────────────────────


class MCPServer:
    """MCP Server for tool registration, discovery, and execution.

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
    """

    def __init__(
        self,
        name: str = "quant-nanggroe-mcp",
        version: str = "0.2.0",
        description: str = "Quant Nanggroe AI MCP Server",
        capabilities: Optional[ServerCapabilities] = None,
    ) -> None:
        """Initialize the MCP server.

        Args:
            name: Server name.
            version: Server version.
            description: Server description.
            capabilities: Server capabilities (defaults to all enabled).
        """
        self._name = name
        self._version = version
        self._description = description
        self._capabilities = capabilities or ServerCapabilities()
        self._tools: Dict[str, ToolHandler] = {}
        self._start_time: float = time.monotonic()
        self._active_connections: int = 0
        self._request_count: int = 0
        self._error_count: int = 0
        self._initialized: bool = False

        logger.info(
            "MCP Server initialized: name=%s, version=%s", name, version
        )

    @property
    def name(self) -> str:
        """Server name."""
        return self._name

    @property
    def version(self) -> str:
        """Server version."""
        return self._version

    @property
    def server_info(self) -> ServerInfo:
        """Server identity and capabilities."""
        return ServerInfo(
            name=self._name,
            version=self._version,
            description=self._description,
            capabilities=self._capabilities,
        )

    @property
    def tools_registered(self) -> int:
        """Number of registered tools."""
        return len(self._tools)

    # ─── Tool Registration ────────────────────────────────────────────────

    def register_tool(self, handler: ToolHandler) -> None:
        """Register a tool handler.

        Args:
            handler: ToolHandler instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        tool_name = handler.definition.name
        if tool_name in self._tools:
            raise ValueError(
                f"Tool {tool_name!r} is already registered. "
                f"Use unregister_tool() first to replace it."
            )
        self._tools[tool_name] = handler
        logger.info(
            "Registered tool: %s (handler=%s)",
            tool_name,
            handler.__class__.__name__,
        )

    def register_function(
        self,
        name: str,
        description: str,
        input_schema: ToolInputSchema,
        func: Callable[..., Any],
        output_schema: Optional[ToolOutputSchema] = None,
        annotations: Optional[Dict[str, Any]] = None,
        async_func: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Register a function as an MCP tool.

        Convenience method that wraps a function in a FunctionToolHandler.

        Args:
            name: Tool name.
            description: Tool description.
            input_schema: Input validation schema.
            func: Synchronous implementation function.
            output_schema: Optional output schema.
            annotations: Optional metadata annotations.
            async_func: Optional async implementation function.
        """
        handler = FunctionToolHandler(
            name=name,
            description=description,
            input_schema=input_schema,
            func=func,
            output_schema=output_schema,
            annotations=annotations,
            async_func=async_func,
        )
        self.register_tool(handler)

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool by name.

        Args:
            name: Tool name to unregister.

        Returns:
            True if the tool was found and removed, False otherwise.
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("Unregistered tool: %s", name)
            return True
        return False

    def get_tool(self, name: str) -> Optional[ToolHandler]:
        """Get a registered tool handler by name.

        Args:
            name: Tool name.

        Returns:
            ToolHandler if found, None otherwise.
        """
        return self._tools.get(name)

    # ─── Request Handling ─────────────────────────────────────────────────

    def handle_request(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Route and handle a JSON-RPC 2.0 request.

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
        """
        self._request_count += 1
        method = request.method

        try:
            # Route to method handler
            if method == "initialize":
                result = self._handle_initialize(request)
            elif method == "tools/list":
                result = self._handle_list_tools(request)
            elif method == "tools/call":
                result = self._handle_call_tool(request)
            elif method == "health":
                result = self._handle_health(request)
            elif method == "notifications/initialized":
                # Client notification, no response needed but we ack
                self._initialized = True
                return make_success_response(request.id, {"status": "acknowledged"})
            else:
                self._error_count += 1
                return make_error_response(
                    error_code=MCPErrorCodes.METHOD_NOT_FOUND,
                    error_message=f"Method {method!r} not found",
                    request_id=request.id,
                )

            return make_success_response(request.id, result)

        except Exception as exc:
            self._error_count += 1
            logger.exception("Error handling request: method=%s", method)
            return make_error_response(
                error_code=MCPErrorCodes.INTERNAL_ERROR,
                error_message=str(exc),
                request_id=request.id,
            )

    async def handle_request_async(
        self, request: JSONRPCRequest
    ) -> JSONRPCResponse:
        """Handle a JSON-RPC 2.0 request asynchronously.

        Same as handle_request but supports async tool execution.

        Args:
            request: JSON-RPC 2.0 request.

        Returns:
            JSON-RPC 2.0 response (success or error).
        """
        self._request_count += 1
        method = request.method

        try:
            if method == "initialize":
                result = self._handle_initialize(request)
            elif method == "tools/list":
                result = self._handle_list_tools(request)
            elif method == "tools/call":
                result = await self._handle_call_tool_async(request)
            elif method == "health":
                result = self._handle_health(request)
            elif method == "notifications/initialized":
                self._initialized = True
                return make_success_response(request.id, {"status": "acknowledged"})
            else:
                self._error_count += 1
                return make_error_response(
                    error_code=MCPErrorCodes.METHOD_NOT_FOUND,
                    error_message=f"Method {method!r} not found",
                    request_id=request.id,
                )

            return make_success_response(request.id, result)

        except Exception as exc:
            self._error_count += 1
            logger.exception("Error handling async request: method=%s", method)
            return make_error_response(
                error_code=MCPErrorCodes.INTERNAL_ERROR,
                error_message=str(exc),
                request_id=request.id,
            )

    # ─── Method Handlers ──────────────────────────────────────────────────

    def _handle_initialize(
        self, request: JSONRPCRequest
    ) -> Dict[str, Any]:
        """Handle the initialize method.

        Args:
            request: Initialize request.

        Returns:
            Initialize result as a dict.
        """
        params = request.params or {}
        init_params = InitializeParams(**params)
        self._initialized = True

        result = InitializeResult(
            server_info=self.server_info,
            protocol_version="2024-11-05",
            capabilities=self._capabilities,
        )

        logger.info(
            "MCP Server initialized by client: %s",
            init_params.client_info.get("name", "unknown"),
        )

        return result.model_dump()

    def _handle_list_tools(
        self, request: JSONRPCRequest
    ) -> Dict[str, Any]:
        """Handle the tools/list method.

        Args:
            request: List tools request.

        Returns:
            ListToolsResult as a dict.
        """
        tools = [
            handler.definition for handler in self._tools.values()
        ]
        result = ListToolsResult(tools=tools)
        return result.model_dump()

    def _handle_call_tool(
        self, request: JSONRPCRequest
    ) -> Dict[str, Any]:
        """Handle the tools/call method synchronously.

        Args:
            request: Call tool request.

        Returns:
            CallToolResult as a dict.
        """
        params = request.params or {}
        call_params = CallToolParams(**params)

        # Find the tool
        handler = self._tools.get(call_params.name)
        if handler is None:
            error_result = ToolCallResult.error_result(
                error_message=f"Tool {call_params.name!r} not found",
                tool_name=call_params.name,
                error_code=MCPErrorCodes.UNKNOWN_TOOL,
            )
            return CallToolResult.from_tool_call_result(error_result).model_dump()

        # Validate arguments
        validation_error = handler.validate_arguments(call_params.arguments)
        if validation_error:
            error_result = ToolCallResult.error_result(
                error_message=validation_error,
                tool_name=call_params.name,
                error_code=MCPErrorCodes.INVALID_PARAMS,
            )
            return CallToolResult.from_tool_call_result(error_result).model_dump()

        # Execute
        result = handler.execute(call_params.arguments)
        return CallToolResult.from_tool_call_result(result).model_dump()

    async def _handle_call_tool_async(
        self, request: JSONRPCRequest
    ) -> Dict[str, Any]:
        """Handle the tools/call method asynchronously.

        Args:
            request: Call tool request.

        Returns:
            CallToolResult as a dict.
        """
        params = request.params or {}
        call_params = CallToolParams(**params)

        # Find the tool
        handler = self._tools.get(call_params.name)
        if handler is None:
            error_result = ToolCallResult.error_result(
                error_message=f"Tool {call_params.name!r} not found",
                tool_name=call_params.name,
                error_code=MCPErrorCodes.UNKNOWN_TOOL,
            )
            return CallToolResult.from_tool_call_result(error_result).model_dump()

        # Validate arguments
        validation_error = handler.validate_arguments(call_params.arguments)
        if validation_error:
            error_result = ToolCallResult.error_result(
                error_message=validation_error,
                tool_name=call_params.name,
                error_code=MCPErrorCodes.INVALID_PARAMS,
            )
            return CallToolResult.from_tool_call_result(error_result).model_dump()

        # Execute asynchronously
        result = await handler.execute_async(call_params.arguments)
        return CallToolResult.from_tool_call_result(result).model_dump()

    def _handle_health(
        self, request: JSONRPCRequest
    ) -> Dict[str, Any]:
        """Handle the health check method.

        Args:
            request: Health check request.

        Returns:
            HealthCheckResult as a dict.
        """
        uptime = time.monotonic() - self._start_time
        error_rate = (
            self._error_count / self._request_count
            if self._request_count > 0
            else 0.0
        )

        status = "healthy"
        if error_rate > 0.5:
            status = "unhealthy"
        elif error_rate > 0.1:
            status = "degraded"

        result = HealthCheckResult(
            status=status,
            version=self._version,
            uptime_seconds=uptime,
            tools_registered=len(self._tools),
            active_connections=self._active_connections,
            details={
                "request_count": self._request_count,
                "error_count": self._error_count,
                "error_rate": round(error_rate, 4),
                "initialized": self._initialized,
                "tool_names": list(self._tools.keys()),
            },
        )
        return result.model_dump()

    # ─── SSE Streaming ────────────────────────────────────────────────────

    async def stream_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        progress_interval_ms: int = 100,
    ) -> Any:
        """Stream tool execution via SSE events.

        Yields SSE events for progress updates and the final result.
        This is the preferred interface for long-running tools.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.
            progress_interval_ms: Interval between progress events.

        Yields:
            SSEEvent objects for progress updates and final result.
        """
        handler = self._tools.get(tool_name)
        if handler is None:
            yield SSEEvent(
                event="error",
                data={
                    "message": f"Tool {tool_name!r} not found",
                    "code": MCPErrorCodes.UNKNOWN_TOOL,
                },
            )
            return

        # Validate
        validation_error = handler.validate_arguments(arguments)
        if validation_error:
            yield SSEEvent(
                event="error",
                data={
                    "message": validation_error,
                    "code": MCPErrorCodes.INVALID_PARAMS,
                },
            )
            return

        # Execute with progress events
        yield SSEEvent(
            event="progress",
            data={"tool_name": tool_name, "status": "started"},
        )

        try:
            # Run in background with progress
            task = asyncio.create_task(handler.execute_async(arguments))
            last_progress = time.monotonic()

            while not task.done():
                await asyncio.sleep(0.01)
                now = time.monotonic()
                if (now - last_progress) * 1000 >= progress_interval_ms:
                    yield SSEEvent(
                        event="progress",
                        data={
                            "tool_name": tool_name,
                            "status": "running",
                            "elapsed_ms": (now - last_progress) * 1000,
                        },
                    )
                    last_progress = now

            result = task.result()
            yield SSEEvent(
                event="result",
                data=CallToolResult.from_tool_call_result(result).model_dump(),
            )
        except Exception as exc:
            yield SSEEvent(
                event="error",
                data={"message": str(exc), "tool_name": tool_name},
            )

    # ─── Utility ──────────────────────────────────────────────────────────

    def list_tool_names(self) -> List[str]:
        """List all registered tool names.

        Returns:
            Sorted list of tool names.
        """
        return sorted(self._tools.keys())

    def get_tool_definitions(self) -> List[ToolDefinition]:
        """Get all tool definitions.

        Returns:
            List of ToolDefinition objects.
        """
        return [handler.definition for handler in self._tools.values()]

    def health_check(self) -> HealthCheckResult:
        """Perform a health check.

        Returns:
            HealthCheckResult with current server status.
        """
        uptime = time.monotonic() - self._start_time
        error_rate = (
            self._error_count / self._request_count
            if self._request_count > 0
            else 0.0
        )

        status = "healthy"
        if error_rate > 0.5:
            status = "unhealthy"
        elif error_rate > 0.1:
            status = "degraded"

        return HealthCheckResult(
            status=status,
            version=self._version,
            uptime_seconds=uptime,
            tools_registered=len(self._tools),
            active_connections=self._active_connections,
            details={
                "request_count": self._request_count,
                "error_count": self._error_count,
                "error_rate": round(error_rate, 4),
                "initialized": self._initialized,
            },
        )
