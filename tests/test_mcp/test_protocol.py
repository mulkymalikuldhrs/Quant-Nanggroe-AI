"""Tests for MCP Protocol types and messages.

Tests all JSON-RPC 2.0 types, MCP-specific types, helper functions,
and serialization roundtrips.
"""

import json
import uuid

import pytest

from quant_nanggroe_ai.mcp.protocol import (
    CallToolParams,
    CallToolResult,
    HealthCheckResult,
    InitializeParams,
    InitializeResult,
    JSONRPCError,
    JSONRPCErrorResponse,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCSuccessResponse,
    JSONRPCVersion,
    MCPErrorCodes,
    SSEEvent,
    ServerCapabilities,
    ServerInfo,
    ToolCallResult,
    ToolDefinition,
    ToolInputSchema,
    ToolOutputSchema,
    make_error_response,
    make_notification,
    make_request,
    make_success_response,
)


# ─── JSON-RPC 2.0 Core Types ─────────────────────────────────────────────────


class TestJSONRPCVersion:
    """Tests for JSONRPCVersion enum."""

    def test_v2_0_value(self):
        assert JSONRPCVersion.V2_0 == "2.0"

    def test_string_comparison(self):
        assert JSONRPCVersion.V2_0 == "2.0"
        assert str(JSONRPCVersion.V2_0) == "JSONRPCVersion.V2_0"


class TestMCPErrorCodes:
    """Tests for MCPErrorCodes enum."""

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


class TestJSONRPCError:
    """Tests for JSONRPCError model."""

    def test_creation(self):
        err = JSONRPCError(code=-32600, message="Invalid Request")
        assert err.code == -32600
        assert err.message == "Invalid Request"
        assert err.data is None

    def test_with_data(self):
        err = JSONRPCError(code=-32602, message="Invalid params", data={"field": "symbol"})
        assert err.data == {"field": "symbol"}

    def test_serialization(self):
        err = JSONRPCError(code=-32700, message="Parse error")
        data = err.model_dump()
        assert data["code"] == -32700
        assert data["message"] == "Parse error"

    def test_min_length_message(self):
        with pytest.raises(Exception):
            JSONRPCError(code=-1, message="")


# ─── Request / Notification / Response ────────────────────────────────────────


class TestJSONRPCRequest:
    """Tests for JSONRPCRequest model."""

    def test_basic_creation(self):
        req = JSONRPCRequest(method="tools/list")
        assert req.jsonrpc == JSONRPCVersion.V2_0
        assert req.method == "tools/list"
        assert req.params is None
        assert isinstance(req.id, str)

    def test_with_params(self):
        req = JSONRPCRequest(
            method="tools/call",
            params={"name": "market_data.get_ohlcv", "arguments": {"symbol": "BTC/USDT"}},
        )
        assert req.params["name"] == "market_data.get_ohlcv"

    def test_custom_id(self):
        req = JSONRPCRequest(method="initialize", id="custom-id-123")
        assert req.id == "custom-id-123"

    def test_integer_id(self):
        req = JSONRPCRequest(method="initialize", id=42)
        assert req.id == 42

    def test_serialization_roundtrip(self):
        req = JSONRPCRequest(method="test", params={"key": "value"}, id="test-id")
        data = req.model_dump()
        restored = JSONRPCRequest(**data)
        assert restored.method == req.method
        assert restored.params == req.params
        assert restored.id == req.id

    def test_method_min_length(self):
        with pytest.raises(Exception):
            JSONRPCRequest(method="")


class TestJSONRPCNotification:
    """Tests for JSONRPCNotification model."""

    def test_creation(self):
        notif = JSONRPCNotification(method="notifications/progress")
        assert notif.jsonrpc == JSONRPCVersion.V2_0
        assert notif.method == "notifications/progress"

    def test_with_params(self):
        notif = JSONRPCNotification(method="notifications/progress", params={"progress": 0.5})
        assert notif.params["progress"] == 0.5


class TestJSONRPCSuccessResponse:
    """Tests for JSONRPCSuccessResponse model."""

    def test_creation(self):
        resp = JSONRPCSuccessResponse(id="req-1", result={"status": "ok"})
        assert resp.jsonrpc == JSONRPCVersion.V2_0
        assert resp.id == "req-1"
        assert resp.result == {"status": "ok"}


class TestJSONRPCErrorResponse:
    """Tests for JSONRPCErrorResponse model."""

    def test_creation(self):
        error = JSONRPCError(code=-32601, message="Method not found")
        resp = JSONRPCErrorResponse(id="req-1", error=error)
        assert resp.error.code == -32601
        assert resp.id == "req-1"

    def test_null_id(self):
        error = JSONRPCError(code=-32700, message="Parse error")
        resp = JSONRPCErrorResponse(error=error)
        assert resp.id is None


# ─── MCP Tool Schema ──────────────────────────────────────────────────────────


class TestToolInputSchema:
    """Tests for ToolInputSchema model."""

    def test_defaults(self):
        schema = ToolInputSchema()
        assert schema.type == "object"
        assert schema.properties == {}
        assert schema.required == []
        assert schema.additional_properties is False

    def test_with_properties(self):
        schema = ToolInputSchema(
            properties={"symbol": {"type": "string"}},
            required=["symbol"],
        )
        assert "symbol" in schema.properties
        assert "symbol" in schema.required


class TestToolDefinition:
    """Tests for ToolDefinition model."""

    def test_creation(self):
        tool = ToolDefinition(
            name="market_data.get_ohlcv",
            description="Fetch OHLCV data",
            input_schema=ToolInputSchema(
                properties={"symbol": {"type": "string"}},
                required=["symbol"],
            ),
        )
        assert tool.name == "market_data.get_ohlcv"
        assert tool.description == "Fetch OHLCV data"
        assert "symbol" in tool.input_schema.required

    def test_name_validation_dot_notation(self):
        tool = ToolDefinition(
            name="market.data.get_ohlcv",
            description="test",
            input_schema=ToolInputSchema(),
        )
        assert tool.name == "market.data.get_ohlcv"

    def test_name_validation_invalid(self):
        with pytest.raises(Exception):
            ToolDefinition(
                name="123invalid",
                description="test",
                input_schema=ToolInputSchema(),
            )

    def test_name_validation_empty(self):
        with pytest.raises(Exception):
            ToolDefinition(name="", description="test", input_schema=ToolInputSchema())

    def test_annotations_default(self):
        tool = ToolDefinition(
            name="test.tool",
            description="test",
            input_schema=ToolInputSchema(),
        )
        assert tool.annotations == {}


class TestToolCallResult:
    """Tests for ToolCallResult model."""

    def test_text_result_factory(self):
        result = ToolCallResult.text_result(text="Hello", tool_name="test.tool")
        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Hello"
        assert result.is_error is False
        assert result.tool_name == "test.tool"

    def test_error_result_factory(self):
        result = ToolCallResult.error_result(
            error_message="Something failed",
            tool_name="test.tool",
            error_code=-32003,
        )
        assert result.is_error is True
        assert "Something failed" in result.content[0]["text"]
        assert result.metadata.get("error_code") == -32003

    def test_json_result_factory(self):
        data = {"price": 50000.0, "symbol": "BTC/USDT"}
        result = ToolCallResult.json_result(data=data, tool_name="test.tool")
        assert result.content[0]["type"] == "text"
        parsed = json.loads(result.content[0]["text"])
        assert parsed["symbol"] == "BTC/USDT"

    def test_execution_time_must_be_non_negative(self):
        with pytest.raises(Exception):
            ToolCallResult(
                content=[{"type": "text", "text": "ok"}],
                tool_name="test.tool",
                execution_time_ms=-1.0,
            )


# ─── Server Info & Capabilities ───────────────────────────────────────────────


class TestServerCapabilities:
    """Tests for ServerCapabilities model."""

    def test_defaults(self):
        caps = ServerCapabilities()
        assert caps.tools is True
        assert caps.resources is False
        assert caps.prompts is False
        assert caps.logging is True
        assert caps.streaming is True
        assert caps.version == "2024-11-05"


class TestServerInfo:
    """Tests for ServerInfo model."""

    def test_creation(self):
        info = ServerInfo(name="test-server", version="1.0.0")
        assert info.name == "test-server"
        assert info.version == "1.0.0"
        assert isinstance(info.capabilities, ServerCapabilities)

    def test_min_length_name(self):
        with pytest.raises(Exception):
            ServerInfo(name="", version="1.0.0")


class TestInitializeParams:
    """Tests for InitializeParams model."""

    def test_creation(self):
        params = InitializeParams(client_info={"name": "test-client", "version": "0.1.0"})
        assert params.client_info["name"] == "test-client"
        assert params.protocol_version == "2024-11-05"


class TestInitializeResult:
    """Tests for InitializeResult model."""

    def test_creation(self):
        server_info = ServerInfo(name="test-server", version="1.0.0")
        result = InitializeResult(server_info=server_info)
        assert result.server_info.name == "test-server"
        assert isinstance(result.capabilities, ServerCapabilities)


class TestHealthCheckResult:
    """Tests for HealthCheckResult model."""

    def test_defaults(self):
        result = HealthCheckResult()
        assert result.status == "healthy"
        assert result.version == "0.1.0"
        assert result.uptime_seconds == 0.0
        assert result.tools_registered == 0
        assert result.active_connections == 0

    def test_valid_statuses(self):
        for status in ("healthy", "degraded", "unhealthy"):
            result = HealthCheckResult(status=status)
            assert result.status == status

    def test_invalid_status(self):
        with pytest.raises(Exception):
            HealthCheckResult(status="broken")

    def test_non_negative_fields(self):
        with pytest.raises(Exception):
            HealthCheckResult(uptime_seconds=-1.0)
        with pytest.raises(Exception):
            HealthCheckResult(tools_registered=-1)
        with pytest.raises(Exception):
            HealthCheckResult(active_connections=-1)


class TestSSEEvent:
    """Tests for SSEEvent model."""

    def test_valid_event_types(self):
        for event_type in ("progress", "result", "error", "ping"):
            ev = SSEEvent(event=event_type)
            assert ev.event == event_type

    def test_invalid_event_type(self):
        with pytest.raises(Exception):
            SSEEvent(event="invalid")

    def test_with_data(self):
        ev = SSEEvent(event="progress", data={"percent": 50})
        assert ev.data["percent"] == 50

    def test_with_id(self):
        ev = SSEEvent(event="result", id="evt-123")
        assert ev.id == "evt-123"


# ─── Helper Functions ──────────────────────────────────────────────────────────


class TestMakeRequest:
    """Tests for make_request helper."""

    def test_basic(self):
        req = make_request(method="tools/list")
        assert isinstance(req, JSONRPCRequest)
        assert req.method == "tools/list"
        assert req.params is None

    def test_with_params(self):
        req = make_request(method="tools/call", params={"name": "test"})
        assert req.params == {"name": "test"}

    def test_custom_id(self):
        req = make_request(method="test", request_id="custom-id")
        assert req.id == "custom-id"


class TestMakeSuccessResponse:
    """Tests for make_success_response helper."""

    def test_basic(self):
        resp = make_success_response(request_id="req-1", result={"ok": True})
        assert isinstance(resp, JSONRPCSuccessResponse)
        assert resp.id == "req-1"
        assert resp.result == {"ok": True}


class TestMakeErrorResponse:
    """Tests for make_error_response helper."""

    def test_basic(self):
        resp = make_error_response(
            error_code=-32601,
            error_message="Method not found",
            request_id="req-1",
        )
        assert isinstance(resp, JSONRPCErrorResponse)
        assert resp.error.code == -32601
        assert resp.id == "req-1"

    def test_with_data(self):
        resp = make_error_response(
            error_code=-32602,
            error_message="Invalid params",
            error_data={"field": "symbol"},
        )
        assert resp.error.data == {"field": "symbol"}


class TestMakeNotification:
    """Tests for make_notification helper."""

    def test_basic(self):
        notif = make_notification(method="notifications/progress")
        assert isinstance(notif, JSONRPCNotification)
        assert notif.method == "notifications/progress"

    def test_with_params(self):
        notif = make_notification(method="notifications/progress", params={"pct": 0.5})
        assert notif.params == {"pct": 0.5}


# ─── CallToolParams / CallToolResult ──────────────────────────────────────────


class TestCallToolParams:
    """Tests for CallToolParams model."""

    def test_creation(self):
        params = CallToolParams(name="market_data.get_ohlcv", arguments={"symbol": "BTC/USDT"})
        assert params.name == "market_data.get_ohlcv"
        assert params.arguments["symbol"] == "BTC/USDT"

    def test_default_arguments(self):
        params = CallToolParams(name="tools/list")
        assert params.arguments == {}

    def test_name_min_length(self):
        with pytest.raises(Exception):
            CallToolParams(name="")


class TestCallToolResult:
    """Tests for CallToolResult model."""

    def test_from_tool_call_result(self):
        tcr = ToolCallResult.text_result(text="Hello", tool_name="test.tool")
        ctr = CallToolResult.from_tool_call_result(tcr)
        assert ctr.content == tcr.content
        assert ctr.is_error is False
        assert ctr.tool_name == "test.tool"
