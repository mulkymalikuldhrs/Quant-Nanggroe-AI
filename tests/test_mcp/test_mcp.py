"""Tests for MCP protocol, server, client, permissions."""
import pytest
from ai_multicolony.mcp.protocol import JSONRPCRequest, JSONRPCResponse, JSONRPCError, JSONRPCErrorCodes
from ai_multicolony.mcp.server import MCPServer
from ai_multicolony.mcp.client import MCPClient
from ai_multicolony.mcp.permissions import PermissionEngine

class TestProtocol:
    def test_request(self):
        r = JSONRPCRequest(method="tools/call", params={"n": "t"})
        assert r.method == "tools/call"
    def test_response(self):
        r = JSONRPCResponse(id="1", result={"ok": True})
        assert r.result == {"ok": True}
    def test_error(self):
        e = JSONRPCError(code=-32601, message="Not found")
        assert e.code == -32601
    def test_error_codes(self):
        assert JSONRPCErrorCodes.PARSE_ERROR == -32700
        assert JSONRPCErrorCodes.PERMISSION_DENIED == -32001

class TestMCPServer:
    def test_create(self): assert MCPServer() is not None
    def test_register_tool(self):
        s = MCPServer()
        s.register_tool(name="test_tool", handler=lambda params, ctx: params, required_level=1, description="test")
        stats = s.get_stats()
        assert stats.get("tool_count", 0) >= 1
    def test_stats(self):
        s = MCPServer()
        stats = s.get_stats()
        assert isinstance(stats, dict)
    def test_audit_log(self):
        s = MCPServer()
        log = s.get_audit_log()
        assert isinstance(log, list)

class TestMCPClient:
    def test_create(self): assert MCPClient() is not None

class TestPermEngine:
    def test_create(self): assert PermissionEngine() is not None
    def test_register_tool(self):
        p = PermissionEngine()
        p.register_tool(tool_name="browser.navigate", required_level=0)
        tools = p.list_tools()
        assert "browser.navigate" in tools
    def test_check_permission(self):
        p = PermissionEngine()
        p.register_tool(tool_name="browser.navigate", required_level=0)
        result = p.check_permission(tool_name="browser.navigate", autonomy_level=0)
        assert result.granted is True
    def test_get_tool_level(self):
        p = PermissionEngine()
        p.register_tool(tool_name="shell.exec", required_level=1)
        level = p.get_tool_level("shell.exec")
        assert level == 1
