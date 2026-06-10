"""Tests for MCP Protocol module."""

from __future__ import annotations

import pytest

from quant_nanggroe_ai.agents.mcp_protocol import (
    MCPTool,
    MCPToolResult,
    MCPServer,
)


# ── Custom test tool ──────────────────────────────────────────────────────

class EchoTool(MCPTool):
    """Simple echo tool for testing."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes back the input"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {"message": {"type": "string"}}}

    async def execute(self, **kwargs) -> dict:
        return {"echo": kwargs.get("message", "")}


class AddTool(MCPTool):
    """Simple addition tool for testing."""

    @property
    def name(self) -> str:
        return "add"

    @property
    def description(self) -> str:
        return "Adds two numbers"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}}

    async def execute(self, **kwargs) -> dict:
        return {"result": kwargs.get("a", 0) + kwargs.get("b", 0)}


# ── MCPToolResult ─────────────────────────────────────────────────────────

class TestMCPToolResult:
    def test_success_result(self):
        result = MCPToolResult(status="success", data={"value": 42})
        assert result.status == "success"
        assert result.data == {"value": 42}
        assert result.error is None

    def test_error_result(self):
        result = MCPToolResult(status="error", error="Something went wrong", error_code="TOOL_ERROR")
        assert result.status == "error"
        assert result.error == "Something went wrong"


# ── MCPServer ─────────────────────────────────────────────────────────────

class TestMCPServer:
    def test_create_server(self):
        server = MCPServer()
        assert server is not None

    def test_register_tool(self):
        server = MCPServer()
        tool = EchoTool()
        server.register_tool(tool)
        tools = server.list_tools()
        # list_tools() returns a list of dicts with 'name' key
        tool_names = [t["name"] if isinstance(t, dict) else t for t in tools]
        assert "echo" in tool_names

    def test_list_tools(self):
        server = MCPServer()
        server.register_tool(EchoTool())
        server.register_tool(AddTool())
        tools = server.list_tools()
        tool_names = [t["name"] if isinstance(t, dict) else t for t in tools]
        assert "echo" in tool_names
        assert "add" in tool_names

    def test_get_tool_schema(self):
        server = MCPServer()
        server.register_tool(EchoTool())
        schema = server.get_tool_schema("echo")
        assert isinstance(schema, dict)

    @pytest.mark.asyncio
    async def test_call_echo_tool(self):
        server = MCPServer()
        server.register_tool(EchoTool())
        result = await server.call_tool("echo", message="hello")
        assert result.status == "success"
        assert result.data == {"echo": "hello"}

    @pytest.mark.asyncio
    async def test_call_add_tool(self):
        server = MCPServer()
        server.register_tool(AddTool())
        result = await server.call_tool("add", a=3, b=7)
        assert result.status == "success"
        assert result.data == {"result": 10}

    @pytest.mark.asyncio
    async def test_call_nonexistent_tool(self):
        server = MCPServer()
        from quant_nanggroe_ai.exceptions import AgentError
        with pytest.raises(AgentError):
            await server.call_tool("nonexistent")

    def test_tool_count(self):
        server = MCPServer()
        count_before = len(server.list_tools())
        server.register_tool(EchoTool())
        assert len(server.list_tools()) == count_before + 1
