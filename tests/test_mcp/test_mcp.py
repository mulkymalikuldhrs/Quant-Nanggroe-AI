"""Comprehensive tests for MCP protocol and tools modules.

Tests cover:
- JSONRPCRequest: create valid request, validate
- JSONRPCResponse: create valid response
- ToolDefinition: schema validation
- ToolCallResult: create result
- MCPToolRegistry (MCPServer): register, list, call tools
- Helper factory functions
- Tool handlers (market data, orders, risk, factors, backtest, portfolio)
- Server capabilities and health check
- SSE events
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from quant_nanggroe.mcp.protocol import (
    JSONRPCVersion,
    MCPErrorCodes,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCNotification,
    JSONRPCSuccessResponse,
    JSONRPCErrorResponse,
    ToolInputSchema,
    ToolOutputSchema,
    ToolDefinition,
    ToolCallResult,
    ServerCapabilities,
    ServerInfo,
    InitializeParams,
    InitializeResult,
    ListToolsResult,
    CallToolParams,
    CallToolResult,
    HealthCheckResult,
    SSEEvent,
    make_request,
    make_success_response,
    make_error_response,
    make_notification,
)
from quant_nanggroe.mcp.server import (
    MCPServer,
    ToolHandler,
    FunctionToolHandler,
)
from quant_nanggroe.mcp.tools import (
    MARKET_DATA_GET_OHLCV,
    MARKET_DATA_GET_TICKER,
    MARKET_DATA_GET_ORDERBOOK,
    ORDERS_PLACE_ORDER,
    ORDERS_CANCEL_ORDER,
    ORDERS_GET_ORDER_STATUS,
    RISK_ASSESS_TRADE,
    RISK_COMPUTE_VAR,
    RISK_COMPUTE_DRAWDOWN,
    FACTORS_LIST,
    FACTORS_COMPUTE,
    BACKTEST_RUN,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. JSON-RPC Request Tests
# ═══════════════════════════════════════════════════════════════════════


class TestJSONRPCRequest:

    def test_make_request(self):
        req = make_request("tools/list", params={})
        assert req.jsonrpc == JSONRPCVersion.V2_0
        assert req.method == "tools/list"
        assert req.id is not None

    def test_request_with_custom_id(self):
        req = make_request("test/method", request_id="custom-123")
        assert req.id == "custom-123"

    def test_request_with_numeric_id(self):
        req = make_request("test/method", request_id=42)
        assert req.id == 42

    def test_request_with_params(self):
        req = make_request("tools/call", params={"name": "test_tool"})
        assert req.params == {"name": "test_tool"}

    def test_request_no_params(self):
        req = make_request("initialize")
        assert req.params is None

    def test_request_method_required(self):
        with pytest.raises(ValidationError):
            JSONRPCRequest(method="")

    def test_request_serialization(self):
        req = make_request("test/method", params={"key": "value"})
        data = req.model_dump()
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test/method"
        assert data["params"] == {"key": "value"}

    def test_request_auto_generated_id(self):
        req1 = make_request("test")
        req2 = make_request("test")
        assert req1.id != req2.id  # UUIDs should be unique

    def test_request_validates_method_min_length(self):
        with pytest.raises(ValidationError):
            JSONRPCRequest(method="")

    def test_request_direct_construction(self):
        req = JSONRPCRequest(
            jsonrpc=JSONRPCVersion.V2_0,
            id="test-id",
            method="initialize",
            params={"client_info": {"name": "test"}},
        )
        assert req.method == "initialize"
        assert req.params["client_info"]["name"] == "test"


# ═══════════════════════════════════════════════════════════════════════
# 2. JSON-RPC Response Tests
# ═══════════════════════════════════════════════════════════════════════


class TestJSONRPCResponse:

    def test_make_success_response(self):
        resp = make_success_response("req-1", {"result": "ok"})
        assert resp.jsonrpc == JSONRPCVersion.V2_0
        assert resp.id == "req-1"
        assert resp.result == {"result": "ok"}

    def test_make_error_response(self):
        resp = make_error_response(
            error_code=MCPErrorCodes.METHOD_NOT_FOUND,
            error_message="Method not found",
            request_id="req-1",
        )
        assert resp.id == "req-1"
        assert resp.error.code == MCPErrorCodes.METHOD_NOT_FOUND
        assert resp.error.message == "Method not found"

    def test_error_response_no_id(self):
        resp = make_error_response(
            error_code=MCPErrorCodes.PARSE_ERROR,
            error_message="Parse error",
        )
        assert resp.id is None

    def test_error_response_with_data(self):
        resp = make_error_response(
            error_code=MCPErrorCodes.INVALID_PARAMS,
            error_message="Invalid params",
            error_data={"field": "symbol"},
        )
        assert resp.error.data == {"field": "symbol"}

    def test_success_serialization(self):
        resp = make_success_response("id-1", {"data": 42})
        data = resp.model_dump()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "id-1"
        assert "result" in data

    def test_error_serialization(self):
        resp = make_error_response(-32601, "Not found", request_id="id-1")
        data = resp.model_dump()
        assert "error" in data
        assert data["error"]["code"] == -32601

    def test_success_response_requires_id(self):
        with pytest.raises(ValidationError):
            JSONRPCSuccessResponse(result="ok")

    def test_error_response_error_required(self):
        with pytest.raises(ValidationError):
            JSONRPCErrorResponse()


# ═══════════════════════════════════════════════════════════════════════
# 3. JSON-RPC Notification Tests
# ═══════════════════════════════════════════════════════════════════════


class TestJSONRPCNotification:

    def test_make_notification(self):
        notif = make_notification("notifications/progress", params={"percent": 50})
        assert notif.jsonrpc == JSONRPCVersion.V2_0
        assert notif.method == "notifications/progress"
        assert notif.params == {"percent": 50}

    def test_notification_has_no_id(self):
        notif = make_notification("test")
        data = notif.model_dump()
        assert "id" not in data or data.get("id") is None

    def test_notification_method_required(self):
        with pytest.raises(ValidationError):
            JSONRPCNotification(method="")

    def test_notification_no_params(self):
        notif = make_notification("test")
        assert notif.params is None


# ═══════════════════════════════════════════════════════════════════════
# 4. JSON-RPC Error and Version Tests
# ═══════════════════════════════════════════════════════════════════════


class TestJSONRPCVersion:

    def test_version_value(self):
        assert JSONRPCVersion.V2_0.value == "2.0"


class TestJSONRPCError:

    def test_error_creation(self):
        err = JSONRPCError(code=-32600, message="Invalid Request")
        assert err.code == -32600
        assert err.message == "Invalid Request"
        assert err.data is None

    def test_error_with_data(self):
        err = JSONRPCError(code=-32602, message="Invalid params", data={"field": "symbol"})
        assert err.data == {"field": "symbol"}

    def test_error_message_required(self):
        with pytest.raises(ValidationError):
            JSONRPCError(code=-32600, message="")


class TestMCPErrorCodes:

    def test_standard_error_codes(self):
        assert MCPErrorCodes.PARSE_ERROR == -32700
        assert MCPErrorCodes.INVALID_REQUEST == -32600
        assert MCPErrorCodes.METHOD_NOT_FOUND == -32601
        assert MCPErrorCodes.INVALID_PARAMS == -32602
        assert MCPErrorCodes.INTERNAL_ERROR == -32603

    def test_mcp_specific_error_codes(self):
        assert MCPErrorCodes.SERVER_NOT_INITIALIZED == -32002
        assert MCPErrorCodes.UNKNOWN_TOOL == -32001
        assert MCPErrorCodes.TOOL_EXECUTION_FAILED == -32003
        assert MCPErrorCodes.RESOURCE_NOT_FOUND == -32004
        assert MCPErrorCodes.RATE_LIMIT_EXCEEDED == -32005
        assert MCPErrorCodes.CAPABILITY_NOT_SUPPORTED == -32006


# ═══════════════════════════════════════════════════════════════════════
# 5. Tool Definition Schema Tests
# ═══════════════════════════════════════════════════════════════════════


class TestToolDefinition:

    def test_valid_tool_definition(self):
        tool = ToolDefinition(
            name="test.tool",
            description="A test tool",
            input_schema=ToolInputSchema(
                type="object",
                properties={"param": {"type": "string"}},
                required=["param"],
            ),
        )
        assert tool.name == "test.tool"
        assert tool.description == "A test tool"

    def test_tool_name_pattern_valid(self):
        tool = ToolDefinition(
            name="valid.tool_name",
            description="Test",
            input_schema=ToolInputSchema(),
        )
        assert tool.name == "valid.tool_name"

    def test_tool_name_invalid_pattern(self):
        with pytest.raises(ValidationError):
            ToolDefinition(
                name="invalid-name!",
                description="Test",
                input_schema=ToolInputSchema(),
            )

    def test_tool_name_starts_with_number_invalid(self):
        with pytest.raises(ValidationError):
            ToolDefinition(
                name="1invalid",
                description="Test",
                input_schema=ToolInputSchema(),
            )

    def test_tool_name_empty_fails(self):
        with pytest.raises(ValidationError):
            ToolDefinition(
                name="",
                description="Test",
                input_schema=ToolInputSchema(),
            )

    def test_tool_description_required(self):
        with pytest.raises(ValidationError):
            ToolDefinition(
                name="test.tool",
                description="",
                input_schema=ToolInputSchema(),
            )

    def test_tool_with_output_schema(self):
        tool = ToolDefinition(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            output_schema=ToolOutputSchema(
                type="object",
                properties={"result": {"type": "string"}},
            ),
        )
        assert tool.output_schema.type == "object"

    def test_tool_with_annotations(self):
        tool = ToolDefinition(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            annotations={"category": "risk", "version": "1.0"},
        )
        assert tool.annotations["category"] == "risk"

    def test_tool_default_output_schema(self):
        tool = ToolDefinition(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
        )
        assert tool.output_schema is not None

    def test_tool_default_annotations(self):
        tool = ToolDefinition(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
        )
        assert tool.annotations == {}

    def test_serialization_round_trip(self):
        tool = ToolDefinition(
            name="test.tool",
            description="A test",
            input_schema=ToolInputSchema(
                properties={"symbol": {"type": "string"}},
                required=["symbol"],
            ),
        )
        data = tool.model_dump()
        tool2 = ToolDefinition(**data)
        assert tool2.name == tool.name
        assert tool2.description == tool.description


class TestToolInputSchema:

    def test_required_fields(self):
        schema = ToolInputSchema(
            properties={"symbol": {"type": "string"}},
            required=["symbol"],
        )
        assert "symbol" in schema.required

    def test_empty_schema(self):
        schema = ToolInputSchema()
        assert schema.properties == {}
        assert schema.required == []
        assert schema.additional_properties is False

    def test_default_type(self):
        schema = ToolInputSchema()
        assert schema.type == "object"

    def test_additional_properties(self):
        schema = ToolInputSchema(additional_properties=True)
        assert schema.additional_properties is True


class TestToolOutputSchema:

    def test_default_schema(self):
        schema = ToolOutputSchema()
        assert schema.type == "object"
        assert schema.properties == {}

    def test_with_properties(self):
        schema = ToolOutputSchema(
            type="object",
            properties={"result": {"type": "string"}, "count": {"type": "integer"}},
        )
        assert len(schema.properties) == 2


# ═══════════════════════════════════════════════════════════════════════
# 6. Tool Call Result Tests
# ═══════════════════════════════════════════════════════════════════════


class TestToolCallResult:

    def test_text_result(self):
        result = ToolCallResult.text_result("Hello", tool_name="test.tool")
        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Hello"
        assert result.is_error is False
        assert result.tool_name == "test.tool"

    def test_error_result(self):
        result = ToolCallResult.error_result("Something failed", tool_name="test.tool")
        assert result.is_error is True
        assert "Something failed" in result.content[0]["text"]

    def test_error_result_with_code(self):
        result = ToolCallResult.error_result(
            "Failed", tool_name="test.tool", error_code=-32003,
        )
        assert result.metadata["error_code"] == -32003

    def test_json_result(self):
        result = ToolCallResult.json_result({"key": "value"}, tool_name="test.tool")
        assert result.content[0]["type"] == "text"
        assert result.is_error is False
        # The content should be valid JSON
        parsed = json.loads(result.content[0]["text"])
        assert parsed["key"] == "value"

    def test_execution_time(self):
        result = ToolCallResult.text_result("ok", tool_name="test", execution_time_ms=150.5)
        assert result.execution_time_ms == 150.5

    def test_execution_time_default(self):
        result = ToolCallResult.text_result("ok", tool_name="test")
        assert result.execution_time_ms == 0.0

    def test_content_required(self):
        with pytest.raises(ValidationError):
            ToolCallResult(content=[], tool_name="test")

    def test_serialization(self):
        result = ToolCallResult.text_result("Hello", tool_name="test.tool")
        data = result.model_dump()
        assert data["tool_name"] == "test.tool"
        assert data["is_error"] is False


class TestCallToolResult:

    def test_from_tool_call_result(self):
        tcr = ToolCallResult.text_result("Result", tool_name="test.tool")
        ctr = CallToolResult.from_tool_call_result(tcr)
        assert ctr.content == tcr.content
        assert ctr.is_error == tcr.is_error
        assert ctr.tool_name == tcr.tool_name

    def test_from_error_tool_call_result(self):
        tcr = ToolCallResult.error_result("Error", tool_name="test.tool")
        ctr = CallToolResult.from_tool_call_result(tcr)
        assert ctr.is_error is True


class TestCallToolParams:

    def test_valid_params(self):
        params = CallToolParams(name="test.tool", arguments={"symbol": "BTC"})
        assert params.name == "test.tool"
        assert params.arguments == {"symbol": "BTC"}

    def test_default_arguments(self):
        params = CallToolParams(name="test.tool")
        assert params.arguments == {}

    def test_name_required(self):
        with pytest.raises(ValidationError):
            CallToolParams()


# ═══════════════════════════════════════════════════════════════════════
# 7. Server Capabilities and Health Tests
# ═══════════════════════════════════════════════════════════════════════


class TestServerCapabilities:

    def test_default_capabilities(self):
        caps = ServerCapabilities()
        assert caps.tools is True
        assert caps.resources is False
        assert caps.prompts is False
        assert caps.logging is True
        assert caps.streaming is True
        assert caps.version == "2024-11-05"

    def test_custom_capabilities(self):
        caps = ServerCapabilities(tools=False, resources=True, streaming=False)
        assert caps.tools is False
        assert caps.resources is True
        assert caps.streaming is False


class TestServerInfo:

    def test_valid_server_info(self):
        info = ServerInfo(name="test-server", version="0.1.0")
        assert info.name == "test-server"
        assert info.version == "0.1.0"

    def test_empty_name_fails(self):
        with pytest.raises(ValidationError):
            ServerInfo(name="", version="0.1.0")

    def test_empty_version_fails(self):
        with pytest.raises(ValidationError):
            ServerInfo(name="test", version="")

    def test_with_description(self):
        info = ServerInfo(name="test", version="0.1.0", description="A test server")
        assert info.description == "A test server"


class TestInitializeParams:

    def test_valid_params(self):
        params = InitializeParams(client_info={"name": "test-client", "version": "1.0"})
        assert params.client_info["name"] == "test-client"

    def test_default_protocol_version(self):
        params = InitializeParams(client_info={"name": "test"})
        assert params.protocol_version == "2024-11-05"


class TestInitializeResult:

    def test_initialize_result(self):
        info = ServerInfo(name="test", version="0.1.0")
        result = InitializeResult(server_info=info)
        assert result.server_info.name == "test"
        assert result.protocol_version == "2024-11-05"


class TestHealthCheckResult:

    def test_healthy(self):
        result = HealthCheckResult(status="healthy")
        assert result.status == "healthy"

    def test_degraded(self):
        result = HealthCheckResult(status="degraded")
        assert result.status == "degraded"

    def test_unhealthy(self):
        result = HealthCheckResult(status="unhealthy")
        assert result.status == "unhealthy"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            HealthCheckResult(status="unknown")

    def test_default_values(self):
        result = HealthCheckResult()
        assert result.tools_registered == 0
        assert result.uptime_seconds == 0.0
        assert result.active_connections == 0


class TestSSEEvent:

    def test_progress_event(self):
        event = SSEEvent(event="progress", data={"percent": 50})
        assert event.event == "progress"

    def test_result_event(self):
        event = SSEEvent(event="result", data={"value": 42})
        assert event.event == "result"

    def test_error_event(self):
        event = SSEEvent(event="error", data={"message": "failed"})
        assert event.event == "error"

    def test_ping_event(self):
        event = SSEEvent(event="ping", data={})
        assert event.event == "ping"

    def test_invalid_event_type(self):
        with pytest.raises(ValidationError):
            SSEEvent(event="invalid", data={})

    def test_event_with_id(self):
        event = SSEEvent(event="result", data={}, id="evt-1")
        assert event.id == "evt-1"

    def test_event_default_no_id(self):
        event = SSEEvent(event="ping", data={})
        assert event.id is None


# ═══════════════════════════════════════════════════════════════════════
# 8. MCP Server (Tool Registry) Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMCPServer:

    def test_server_creation(self):
        server = MCPServer(name="test-server", version="0.1.0")
        assert server.name == "test-server"
        assert server.version == "0.1.0"
        assert server.tools_registered == 0

    def test_server_info_property(self):
        server = MCPServer(name="test", version="1.0")
        info = server.server_info
        assert isinstance(info, ServerInfo)
        assert info.name == "test"

    def test_register_tool_handler(self):
        server = MCPServer()

        class TestHandler(ToolHandler):
            @property
            def definition(self):
                return ToolDefinition(
                    name="test.tool",
                    description="Test",
                    input_schema=ToolInputSchema(),
                )

            def execute(self, arguments):
                return ToolCallResult.text_result("ok", tool_name="test.tool")

        handler = TestHandler()
        server.register_tool(handler)
        assert server.tools_registered == 1

    def test_register_function_tool(self):
        server = MCPServer()

        def my_func(symbol: str) -> dict:
            return {"symbol": symbol}

        server.register_function(
            name="test.get_data",
            description="Get data",
            input_schema=ToolInputSchema(
                properties={"symbol": {"type": "string"}},
                required=["symbol"],
            ),
            func=my_func,
        )
        assert server.tools_registered == 1

    def test_register_duplicate_tool_raises(self):
        server = MCPServer()

        def my_func(symbol: str) -> dict:
            return {"symbol": symbol}

        server.register_function(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            func=my_func,
        )
        with pytest.raises(ValueError, match="already registered"):
            server.register_function(
                name="test.tool",
                description="Test 2",
                input_schema=ToolInputSchema(),
                func=my_func,
            )

    def test_unregister_tool(self):
        server = MCPServer()
        server.register_function(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            func=lambda: {},
        )
        assert server.unregister_tool("test.tool") is True
        assert server.tools_registered == 0

    def test_unregister_nonexistent(self):
        server = MCPServer()
        assert server.unregister_tool("nonexistent") is False

    def test_get_tool(self):
        server = MCPServer()
        server.register_function(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            func=lambda: {"result": "ok"},
        )
        handler = server.get_tool("test.tool")
        assert handler is not None
        assert handler.definition.name == "test.tool"

    def test_get_tool_nonexistent(self):
        server = MCPServer()
        assert server.get_tool("nonexistent") is None

    def test_list_tool_names(self):
        server = MCPServer()
        server.register_function(
            name="alpha.tool",
            description="A",
            input_schema=ToolInputSchema(),
            func=lambda: {},
        )
        server.register_function(
            name="beta.tool",
            description="B",
            input_schema=ToolInputSchema(),
            func=lambda: {},
        )
        names = server.list_tool_names()
        assert names == ["alpha.tool", "beta.tool"]  # Sorted

    def test_get_tool_definitions(self):
        server = MCPServer()
        server.register_function(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            func=lambda: {},
        )
        defs = server.get_tool_definitions()
        assert len(defs) == 1
        assert isinstance(defs[0], ToolDefinition)

    def test_handle_initialize(self):
        server = MCPServer(name="test", version="0.1.0")
        req = make_request("initialize", params={
            "client_info": {"name": "test-client", "version": "1.0"},
        })
        resp = server.handle_request(req)
        assert isinstance(resp, JSONRPCSuccessResponse)
        assert resp.result["server_info"]["name"] == "test"

    def test_handle_list_tools(self):
        server = MCPServer()
        server.register_function(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            func=lambda: {},
        )
        req = make_request("tools/list")
        resp = server.handle_request(req)
        assert isinstance(resp, JSONRPCSuccessResponse)
        assert len(resp.result["tools"]) == 1

    def test_handle_call_tool(self):
        server = MCPServer()
        server.register_function(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(
                properties={"symbol": {"type": "string"}},
                required=["symbol"],
            ),
            func=lambda symbol: {"symbol": symbol.upper()},
        )
        req = make_request("tools/call", params={
            "name": "test.tool",
            "arguments": {"symbol": "btc"},
        })
        resp = server.handle_request(req)
        assert isinstance(resp, JSONRPCSuccessResponse)

    def test_handle_call_unknown_tool(self):
        server = MCPServer()
        req = make_request("tools/call", params={
            "name": "nonexistent",
            "arguments": {},
        })
        resp = server.handle_request(req)
        assert isinstance(resp, JSONRPCSuccessResponse)
        # The result should indicate an error
        assert resp.result.get("is_error") is True

    def test_handle_call_tool_missing_args(self):
        server = MCPServer()
        server.register_function(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(
                properties={"symbol": {"type": "string"}},
                required=["symbol"],
            ),
            func=lambda symbol: {"symbol": symbol},
        )
        req = make_request("tools/call", params={
            "name": "test.tool",
            "arguments": {},  # Missing required "symbol"
        })
        resp = server.handle_request(req)
        assert isinstance(resp, JSONRPCSuccessResponse)
        assert resp.result.get("is_error") is True

    def test_handle_unknown_method(self):
        server = MCPServer()
        req = make_request("unknown/method")
        resp = server.handle_request(req)
        assert isinstance(resp, JSONRPCErrorResponse)
        assert resp.error.code == MCPErrorCodes.METHOD_NOT_FOUND

    def test_handle_health(self):
        server = MCPServer()
        req = make_request("health")
        resp = server.handle_request(req)
        assert isinstance(resp, JSONRPCSuccessResponse)
        assert resp.result["status"] in ("healthy", "degraded", "unhealthy")

    def test_health_check_direct(self):
        server = MCPServer()
        result = server.health_check()
        assert isinstance(result, HealthCheckResult)
        assert result.status == "healthy"

    def test_notifications_initialized(self):
        server = MCPServer()
        req = make_request("notifications/initialized")
        resp = server.handle_request(req)
        assert isinstance(resp, JSONRPCSuccessResponse)


# ═══════════════════════════════════════════════════════════════════════
# 9. FunctionToolHandler Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFunctionToolHandler:

    def test_execute_success(self):
        handler = FunctionToolHandler(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            func=lambda: {"result": "ok"},
        )
        result = handler.execute({})
        assert result.is_error is False
        assert result.tool_name == "test.tool"

    def test_execute_with_args(self):
        handler = FunctionToolHandler(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(
                properties={"symbol": {"type": "string"}},
                required=["symbol"],
            ),
            func=lambda symbol: {"symbol": symbol.upper()},
        )
        result = handler.execute({"symbol": "btc"})
        assert result.is_error is False

    def test_execute_error(self):
        def failing_func():
            raise ValueError("Something went wrong")

        handler = FunctionToolHandler(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
            func=failing_func,
        )
        result = handler.execute({})
        assert result.is_error is True
        assert "Something went wrong" in result.content[0]["text"]

    def test_definition_property(self):
        handler = FunctionToolHandler(
            name="test.tool",
            description="Test description",
            input_schema=ToolInputSchema(),
            func=lambda: {},
        )
        defn = handler.definition
        assert isinstance(defn, ToolDefinition)
        assert defn.name == "test.tool"
        assert defn.description == "Test description"

    def test_validate_arguments_missing_required(self):
        handler = FunctionToolHandler(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(
                properties={"symbol": {"type": "string"}},
                required=["symbol"],
            ),
            func=lambda symbol: {},
        )
        error = handler.validate_arguments({})
        assert error is not None
        assert "symbol" in error

    def test_validate_arguments_unknown_field(self):
        handler = FunctionToolHandler(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(additional_properties=False),
            func=lambda: {},
        )
        error = handler.validate_arguments({"unknown_field": "value"})
        assert error is not None
        assert "unknown" in error.lower()

    def test_validate_arguments_valid(self):
        handler = FunctionToolHandler(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(
                properties={"symbol": {"type": "string"}},
                required=["symbol"],
            ),
            func=lambda symbol: {},
        )
        error = handler.validate_arguments({"symbol": "BTC"})
        assert error is None


# ═══════════════════════════════════════════════════════════════════════
# 10. MCP Tool Schema Definitions Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMCPToolSchemas:
    """Verify the predefined tool schemas are valid."""

    def test_market_data_ohlcv_schema(self):
        assert MARKET_DATA_GET_OHLCV.name == "market_data.get_ohlcv"
        assert "symbol" in MARKET_DATA_GET_OHLCV.input_schema.properties
        assert "symbol" in MARKET_DATA_GET_OHLCV.input_schema.required

    def test_market_data_ticker_schema(self):
        assert MARKET_DATA_GET_TICKER.name == "market_data.get_ticker"
        assert "symbol" in MARKET_DATA_GET_TICKER.input_schema.required

    def test_market_data_orderbook_schema(self):
        assert MARKET_DATA_GET_ORDERBOOK.name == "market_data.get_orderbook"

    def test_orders_place_order_schema(self):
        assert ORDERS_PLACE_ORDER.name == "orders.place_order"
        required = ORDERS_PLACE_ORDER.input_schema.required
        assert "symbol" in required
        assert "side" in required
        assert "quantity" in required

    def test_orders_cancel_order_schema(self):
        assert ORDERS_CANCEL_ORDER.name == "orders.cancel_order"
        assert "order_id" in ORDERS_CANCEL_ORDER.input_schema.required

    def test_orders_get_order_status_schema(self):
        assert ORDERS_GET_ORDER_STATUS.name == "orders.get_order_status"
        assert "order_id" in ORDERS_GET_ORDER_STATUS.input_schema.required

    def test_risk_assess_trade_schema(self):
        assert RISK_ASSESS_TRADE.name == "risk.assess_trade"
        required = RISK_ASSESS_TRADE.input_schema.required
        assert "symbol" in required
        assert "direction" in required
        assert "lot_size" in required
        assert "entry" in required
        assert "stop_loss" in required

    def test_risk_compute_var_schema(self):
        assert RISK_COMPUTE_VAR.name == "risk.compute_var"
        assert "portfolio_value" in RISK_COMPUTE_VAR.input_schema.required

    def test_risk_compute_drawdown_schema(self):
        assert RISK_COMPUTE_DRAWDOWN.name == "risk.compute_drawdown"
        required = RISK_COMPUTE_DRAWDOWN.input_schema.required
        assert "portfolio_value" in required
        assert "peak_value" in required
        assert "current_value" in required

    def test_factors_list_schema(self):
        assert FACTORS_LIST.name == "factors.list"

    def test_factors_compute_schema(self):
        assert FACTORS_COMPUTE.name == "factors.compute"
        assert "factor_id" in FACTORS_COMPUTE.input_schema.required

    def test_backtest_run_schema(self):
        assert BACKTEST_RUN.name == "backtest.run"


# ═══════════════════════════════════════════════════════════════════════
# 11. MCP Tool Handler Function Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMCPToolHandlers:
    """Test the actual tool handler functions."""

    def test_market_data_get_ohlcv(self):
        from quant_nanggroe.mcp.tools import _market_data_get_ohlcv
        result = _market_data_get_ohlcv(symbol="BTC/USDT", timeframe="1d", limit=100)
        assert result["symbol"] == "BTC/USDT"
        assert result["timeframe"] == "1d"
        assert "data" in result

    def test_market_data_get_ticker(self):
        from quant_nanggroe.mcp.tools import _market_data_get_ticker
        result = _market_data_get_ticker(symbol="AAPL")
        assert result["symbol"] == "AAPL"
        assert "last_price" in result

    def test_market_data_get_orderbook(self):
        from quant_nanggroe.mcp.tools import _market_data_get_orderbook
        result = _market_data_get_orderbook(symbol="BTC/USDT", limit=10)
        assert result["symbol"] == "BTC/USDT"
        assert "bids" in result
        assert "asks" in result

    def test_market_data_get_market_data(self):
        from quant_nanggroe.mcp.tools import _market_data_get_market_data
        result = _market_data_get_market_data(
            symbol="BTC/USDT",
            include_ohlcv=True,
            include_ticker=True,
        )
        assert "ohlcv" in result
        assert "ticker" in result

    def test_market_data_get_market_data_no_orderbook(self):
        from quant_nanggroe.mcp.tools import _market_data_get_market_data
        result = _market_data_get_market_data(
            symbol="BTC/USDT",
            include_orderbook=False,
        )
        assert "orderbook" not in result

    def test_market_data_get_market_data_with_orderbook(self):
        from quant_nanggroe.mcp.tools import _market_data_get_market_data
        result = _market_data_get_market_data(
            symbol="BTC/USDT",
            include_orderbook=True,
        )
        assert "orderbook" in result

    def test_orders_place_order_valid(self):
        from quant_nanggroe.mcp.tools import _orders_place_order
        result = _orders_place_order(
            symbol="BTC/USDT", side="buy", quantity=0.1, order_type="market",
        )
        assert result["status"] == "submitted"
        assert result["symbol"] == "BTC/USDT"
        assert "order_id" in result

    def test_orders_place_order_invalid_side(self):
        from quant_nanggroe.mcp.tools import _orders_place_order
        result = _orders_place_order(
            symbol="BTC/USDT", side="invalid", quantity=0.1,
        )
        assert result["status"] == "rejected"
        assert "error" in result

    def test_orders_place_order_invalid_type(self):
        from quant_nanggroe.mcp.tools import _orders_place_order
        result = _orders_place_order(
            symbol="BTC/USDT", side="buy", quantity=0.1, order_type="invalid",
        )
        assert result["status"] == "rejected"

    def test_orders_cancel_order(self):
        from quant_nanggroe.mcp.tools import _orders_cancel_order
        result = _orders_cancel_order(order_id="ORD-123")
        assert result["status"] == "cancel_requested"
        assert result["order_id"] == "ORD-123"

    def test_orders_get_order_status(self):
        from quant_nanggroe.mcp.tools import _orders_get_order_status
        result = _orders_get_order_status(order_id="ORD-123")
        assert result["order_id"] == "ORD-123"

    def test_risk_compute_var(self):
        from quant_nanggroe.mcp.tools import _risk_compute_var
        result = _risk_compute_var(portfolio_value=1_000_000)
        assert "var_value" in result
        assert "cvar_value" in result
        assert result["confidence_level"] == 0.95

    def test_risk_compute_drawdown(self):
        from quant_nanggroe.mcp.tools import _risk_compute_drawdown
        result = _risk_compute_drawdown(
            portfolio_value=1_000_000,
            peak_value=1_100_000,
            current_value=950_000,
        )
        assert result["current_drawdown"] > 0
        assert result["peak_value"] == 1_100_000

    def test_risk_compute_drawdown_no_drawdown(self):
        from quant_nanggroe.mcp.tools import _risk_compute_drawdown
        result = _risk_compute_drawdown(
            portfolio_value=1_000_000,
            peak_value=1_100_000,
            current_value=1_100_000,
        )
        # When current == peak, drawdown is 0
        assert result["current_drawdown"] == 0.0

    def test_factors_list(self):
        from quant_nanggroe.mcp.tools import _factors_list
        result = _factors_list(zoo="technical")
        assert "factors" in result
        assert result["count"] >= 0

    def test_factors_compute_no_data(self):
        from quant_nanggroe.mcp.tools import _factors_compute
        result = _factors_compute(factor_id="rsi_14")
        assert "error" in result

    def test_backtest_run(self):
        from quant_nanggroe.mcp.tools import _backtest_run
        result = _backtest_run(symbols=["SPY"], strategy_type="signal_based")
        assert result["status"] == "completed"
        assert "metrics" in result

    def test_portfolio_get(self):
        from quant_nanggroe.mcp.tools import _portfolio_get
        result = _portfolio_get()
        assert "total_value" in result
        assert "positions" in result

    def test_portfolio_get_positions(self):
        from quant_nanggroe.mcp.tools import _portfolio_get_positions
        result = _portfolio_get_positions()
        assert "positions" in result

    def test_portfolio_get_position(self):
        from quant_nanggroe.mcp.tools import _portfolio_get_position
        result = _portfolio_get_position(symbol="AAPL")
        assert result["symbol"] == "AAPL"

    def test_portfolio_get_performance(self):
        from quant_nanggroe.mcp.tools import _portfolio_get_performance
        result = _portfolio_get_performance()
        assert "total_return" in result
        assert "sharpe_ratio" in result


# ═══════════════════════════════════════════════════════════════════════
# 12. Helper Factory Function Tests
# ═══════════════════════════════════════════════════════════════════════


class TestHelperFunctions:

    def test_make_request_returns_correct_type(self):
        req = make_request("test")
        assert isinstance(req, JSONRPCRequest)

    def test_make_success_response_returns_correct_type(self):
        resp = make_success_response("id-1", result="ok")
        assert isinstance(resp, JSONRPCSuccessResponse)

    def test_make_error_response_returns_correct_type(self):
        resp = make_error_response(-32601, "Not found", request_id="id-1")
        assert isinstance(resp, JSONRPCErrorResponse)

    def test_make_notification_returns_correct_type(self):
        notif = make_notification("test")
        assert isinstance(notif, JSONRPCNotification)

    def test_make_request_with_all_params(self):
        req = make_request(
            method="tools/call",
            params={"name": "test"},
            request_id="custom-id",
        )
        assert req.method == "tools/call"
        assert req.params == {"name": "test"}
        assert req.id == "custom-id"

    def test_make_error_response_with_all_params(self):
        resp = make_error_response(
            error_code=-32602,
            error_message="Invalid params",
            request_id="req-1",
            error_data={"field": "symbol"},
        )
        assert resp.error.code == -32602
        assert resp.error.data == {"field": "symbol"}


# ═══════════════════════════════════════════════════════════════════════
# 13. ListToolsResult Tests
# ═══════════════════════════════════════════════════════════════════════


class TestListToolsResult:

    def test_empty_tools(self):
        result = ListToolsResult()
        assert result.tools == []

    def test_with_tools(self):
        tool = ToolDefinition(
            name="test.tool",
            description="Test",
            input_schema=ToolInputSchema(),
        )
        result = ListToolsResult(tools=[tool])
        assert len(result.tools) == 1
