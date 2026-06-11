"""Tool API routes.

Endpoints:
* GET  /api/v1/tools           – list tools
* GET  /api/v1/tools/{name}    – describe tool
* POST /api/v1/tools/{name}/call – call tool
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException

from ..schemas import (
    ToolListResponse,
    ToolDescribeResponse,
    ToolCallRequest,
    ToolCallResponse,
)

logger = logging.getLogger(__name__)


class ToolRoutes:
    """Route handlers for tool operations."""

    def __init__(self, mcp_server: Any = None):
        self._mcp_server = mcp_server

    async def list_tools(self, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/tools – list all available tools."""
        if self._mcp_server and hasattr(self._mcp_server, "_tools"):
            tools = [
                {
                    "name": name,
                    "category": getattr(tool, "category", "unknown").value if hasattr(tool, "category") else "unknown",
                    "description": getattr(tool, "description", ""),
                }
                for name, tool in self._mcp_server._tools.items()
            ]
            return ToolListResponse(tools=tools, total=len(tools)).model_dump(mode="json")

        if self._mcp_server and hasattr(self._mcp_server, "list_tools"):
            tools = self._mcp_server.list_tools()
            return ToolListResponse(tools=tools, total=len(tools)).model_dump(mode="json")

        logger.warning("tool_list_stub - MCPServer not injected, raising 503")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Tool service unavailable - MCPServer not configured",
                "code": "SERVICE_UNAVAILABLE",
                "warning": "MCPServer not configured - no tools available",
            },
        )

    async def describe_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/tools/{name} – describe a specific tool."""
        if self._mcp_server and hasattr(self._mcp_server, "_tools"):
            tool = self._mcp_server._tools.get(tool_name)
            if tool:
                return ToolDescribeResponse(
                    name=tool_name,
                    category=getattr(tool, "category", "unknown").value if hasattr(tool, "category") else "unknown",
                    description=getattr(tool, "description", ""),
                    required_autonomy=getattr(tool, "required_autonomy", 1).value if hasattr(getattr(tool, "required_autonomy", None), "value") else getattr(tool, "required_autonomy", 1),
                    parameters=getattr(tool, "parameters", {}),
                    returns=getattr(tool, "returns", {}),
                    dangerous=getattr(tool, "dangerous", False),
                ).model_dump(mode="json")

        return {"error": f"Tool {tool_name} not found", "code": "TOOL_NOT_FOUND"}

    async def call_tool(self, tool_name: str, request: Optional[ToolCallRequest] = None, **kwargs: Any) -> Dict[str, Any]:
        """POST /api/v1/tools/{name}/call – invoke a tool."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = ToolCallRequest(
                arguments=data.get("arguments", {}),
                agent_id=data.get("agent_id", ""),
                autonomy_level=data.get("autonomy_level", 0),
            )

        if self._mcp_server and hasattr(self._mcp_server, "handle_request"):
            from ...types import MCPRequest
            rpc_req = MCPRequest(
                method="tools/call",
                params={
                    "name": tool_name,
                    "arguments": request.arguments,
                    "context": {
                        "agent_id": request.agent_id,
                        "autonomy_level": request.autonomy_level,
                    },
                },
            )
            try:
                response = await self._mcp_server.handle_request(rpc_req)
                return ToolCallResponse(
                    call_id=rpc_req.id,
                    tool_name=tool_name,
                    status="success" if not response.error else "error",
                    data=response.result,
                    error=response.error.get("message") if response.error else None,
                ).model_dump(mode="json")
            except Exception as exc:
                return ToolCallResponse(
                    call_id=rpc_req.id,
                    tool_name=tool_name,
                    status="error",
                    error=str(exc),
                ).model_dump(mode="json")

        logger.error("tool_call_stub - MCPServer not injected, cannot call tool %s, raising 503", tool_name)
        raise HTTPException(
            status_code=503,
            detail={
                "error": f"Tool {tool_name} unavailable - MCPServer not configured",
                "code": "SERVICE_UNAVAILABLE",
            },
        )
