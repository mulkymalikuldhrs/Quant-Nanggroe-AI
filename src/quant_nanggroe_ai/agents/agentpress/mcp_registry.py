"""
MCP Registry - Registry for MCP (Model Context Protocol) tool discovery and management.

Adapted from suna AgentPress for Quant-Nanggroe-AI trading platform.
Manages MCP tool lifecycle: discovery, activation, execution, and schema caching.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

from quant_nanggroe_ai.agents.agentpress.tool import ToolResult

logger = logging.getLogger(__name__)


class MCPToolStatus(Enum):
    """Status of an MCP tool in the registry."""
    DISCOVERED = "discovered"
    LOADING = "loading"
    ACTIVE = "active"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class MCPToolInfo:
    """Information about an MCP tool.
    
    Attributes:
        tool_name: Name of the tool
        toolkit_slug: Slug identifying the toolkit this tool belongs to
        mcp_config: Configuration for connecting to the MCP server
        status: Current status of the tool
        load_time_ms: Time taken to load the tool (ms)
        last_used_ms: Timestamp of last usage
        call_count: Number of times the tool has been called
        schema: OpenAPI schema for the tool
        description: Tool description
        instance: Tool instance (if loaded)
        last_error: Last error message
        error_count: Number of errors
    """
    tool_name: str
    toolkit_slug: str
    mcp_config: Dict[str, Any]
    status: MCPToolStatus = MCPToolStatus.DISCOVERED
    
    load_time_ms: Optional[float] = None
    last_used_ms: Optional[float] = None
    call_count: int = 0
    
    schema: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    instance: Optional[Any] = None
    
    last_error: Optional[str] = None
    error_count: int = 0


@dataclass
class MCPExecutionContext:
    """Context for MCP tool execution.
    
    Attributes:
        user_context: User-specific context for the execution
        execution_stats: Statistics about tool executions
    """
    user_context: Dict[str, Any] = field(default_factory=dict)
    execution_stats: Dict[str, Any] = field(default_factory=lambda: {
        'tools_executed': 0,
        'total_execution_time_ms': 0,
        'cache_hits': 0,
        'activation_requests': 0
    })


class MCPRegistry:
    """Registry for managing MCP tools with discovery, activation, and execution.
    
    Adapted from suna AgentPress for Quant-Nanggroe-AI.
    Supports SSE, HTTP, and stdio MCP server transports.
    
    Usage:
        registry = MCPRegistry()
        registry.register_tool_info(MCPToolInfo(
            tool_name="get_stock_data",
            toolkit_slug="financial_data",
            mcp_config={"url": "http://mcp-server:8080"}
        ))
        result = await registry.execute_tool("get_stock_data", {"symbol": "AAPL"}, ctx)
    """
    
    SCHEMA_CACHE_TTL_HOURS = 24
    SCHEMA_CACHE_KEY_PREFIX = "mcp_schema:"
    
    def __init__(self):
        self._tools: Dict[str, MCPToolInfo] = {}
        self._toolkit_mapping: Dict[str, Set[str]] = {}
        self._status_index: Dict[MCPToolStatus, Set[str]] = {
            status: set() for status in MCPToolStatus
        }
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        self._redis_client = None
        
        logger.info("Initialized MCP tool registry")
    
    def register_tool_info(self, tool_info: MCPToolInfo) -> None:
        """Register information about an MCP tool.
        
        Args:
            tool_info: Information about the tool to register
        """
        tool_name = tool_info.tool_name
        self._tools[tool_name] = tool_info
        
        toolkit = tool_info.toolkit_slug
        if toolkit not in self._toolkit_mapping:
            self._toolkit_mapping[toolkit] = set()
        self._toolkit_mapping[toolkit].add(tool_name)
        
        self._status_index[tool_info.status].add(tool_name)
        
        logger.debug(f"Registered MCP tool {tool_name} from {toolkit}")
    
    def activate_tool(self, tool_name: str, instance: Any, schema: Optional[Dict] = None) -> bool:
        """Activate a tool by providing its instance and schema.
        
        Args:
            tool_name: Name of the tool to activate
            instance: Tool instance
            schema: Optional OpenAPI schema
            
        Returns:
            True if activation succeeded
        """
        if tool_name not in self._tools:
            logger.warning(f"Cannot activate unknown tool: {tool_name}")
            return False
        
        tool_info = self._tools[tool_name]
        self._update_tool_status(tool_name, MCPToolStatus.ACTIVE)
        
        tool_info.instance = instance
        tool_info.schema = schema
        tool_info.load_time_ms = time.time() * 1000
        
        logger.info(f"Activated MCP tool {tool_name}")
        return True
    
    def _update_tool_status(self, tool_name: str, new_status: MCPToolStatus) -> None:
        """Update the status of a tool in the registry."""
        if tool_name not in self._tools:
            return
        
        tool_info = self._tools[tool_name]
        old_status = tool_info.status
        
        if tool_name in self._status_index[old_status]:
            self._status_index[old_status].remove(tool_name)
        self._status_index[new_status].add(tool_name)
        
        tool_info.status = new_status
    
    def get_tool_info(self, tool_name: str) -> Optional[MCPToolInfo]:
        """Get information about a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            MCPToolInfo or None if not found
        """
        return self._tools.get(tool_name)
    
    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is registered (any status).
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if the tool is registered
        """
        return tool_name in self._tools
    
    def is_tool_active(self, tool_name: str) -> bool:
        """Check if a tool is active and ready for execution.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if the tool is in ACTIVE status
        """
        tool_info = self._tools.get(tool_name)
        return tool_info is not None and tool_info.status == MCPToolStatus.ACTIVE
    
    def get_tools_by_status(self, status: MCPToolStatus) -> List[str]:
        """Get tool names filtered by status.
        
        Args:
            status: Status to filter by
            
        Returns:
            List of tool names with the given status
        """
        return list(self._status_index[status])
    
    def get_tools_by_toolkit(self, toolkit_slug: str) -> List[str]:
        """Get tool names belonging to a toolkit.
        
        Args:
            toolkit_slug: Toolkit slug to filter by
            
        Returns:
            List of tool names in the toolkit
        """
        return list(self._toolkit_mapping.get(toolkit_slug, set()))
    
    def get_available_toolkits(self) -> List[str]:
        """Get all available toolkit slugs.
        
        Returns:
            List of toolkit slugs
        """
        return list(self._toolkit_mapping.keys())
    
    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        context: Optional[MCPExecutionContext] = None
    ) -> ToolResult:
        """Execute an MCP tool.
        
        Args:
            tool_name: Name of the tool to execute
            args: Arguments to pass to the tool
            context: Optional execution context
            
        Returns:
            ToolResult with execution results
        """
        if context is None:
            context = MCPExecutionContext()
        
        start_time = time.time()
        
        try:
            if not self.is_tool_available(tool_name):
                return ToolResult(success=False, output=f"MCP tool '{tool_name}' not found in registry")
            
            tool_info = self._tools[tool_name]
            
            if not self.is_tool_active(tool_name):
                logger.info(f"Auto-activating MCP tool {tool_name}")
                # For now, just check if instance is available
                if not tool_info.instance:
                    return ToolResult(success=False, output=f"MCP tool {tool_name} is not active and has no instance")
            
            tool_info = self._tools[tool_name]
            if not tool_info.instance:
                return ToolResult(success=False, output=f"MCP tool {tool_name} has no active instance")
            
            # Call the tool method
            method = getattr(tool_info.instance, tool_name)
            result = await method(**args) if args else await method()
            
            # Update statistics
            execution_time_ms = (time.time() - start_time) * 1000
            tool_info.call_count += 1
            tool_info.last_used_ms = time.time() * 1000
            context.execution_stats['tools_executed'] += 1
            context.execution_stats['total_execution_time_ms'] += execution_time_ms
            
            logger.debug(f"MCP tool {tool_name} executed in {execution_time_ms:.1f}ms")
            return result
            
        except Exception as e:
            tool_info = self._tools.get(tool_name)
            if tool_info:
                tool_info.last_error = str(e)
                tool_info.error_count += 1
                self._update_tool_status(tool_name, MCPToolStatus.FAILED)
            
            logger.error(f"MCP tool {tool_name} execution failed: {e}")
            return ToolResult(success=False, output=f"MCP tool execution error: {str(e)}")
    
    async def discover_schemas_from_mcp(
        self,
        transport_type: str,
        config: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Discover tool schemas from an MCP server.
        
        Args:
            transport_type: Transport type ('sse', 'http', or 'stdio')
            config: Configuration for connecting to the MCP server
            
        Returns:
            Dict mapping tool names to their OpenAPI schemas
        """
        schemas = {}
        
        try:
            if transport_type == "sse":
                schemas = await self._load_sse_mcp_schemas(config)
            elif transport_type == "http":
                schemas = await self._load_http_mcp_schemas(config)
            elif transport_type == "stdio":
                schemas = await self._load_stdio_mcp_schemas(config)
            else:
                schemas = await self._load_http_mcp_schemas(config)
        except Exception as e:
            logger.error(f"Failed to discover schemas from MCP server ({transport_type}): {e}")
        
        return schemas
    
    async def _load_sse_mcp_schemas(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Load schemas from SSE MCP server."""
        url = config.get('url')
        if not url:
            logger.error("Missing 'url' in SSE MCP config")
            return {}
        
        try:
            from mcp.client.sse import sse_client
            from mcp import ClientSession
        except ImportError:
            logger.error("mcp package not installed. Install with: pip install mcp")
            return {}
        
        headers = config.get('headers', {})
        schemas = {}
        
        try:
            async with sse_client(url, headers=headers) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    tools = tools_result.tools if hasattr(tools_result, 'tools') else tools_result
                    
                    for tool in tools:
                        schema = {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description or f"Execute {tool.name}",
                                "parameters": getattr(tool, 'inputSchema', {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                })
                            }
                        }
                        schemas[tool.name] = schema
        except Exception as e:
            logger.error(f"Failed to load SSE schemas: {e}")
        
        return schemas
    
    async def _load_http_mcp_schemas(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Load schemas from HTTP/Streamable HTTP MCP server."""
        url = config.get('url')
        if not url:
            logger.error("Missing 'url' in HTTP MCP config")
            return {}
        
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from mcp import ClientSession
        except ImportError:
            logger.error("mcp package not installed. Install with: pip install mcp")
            return {}
        
        schemas = {}
        
        try:
            async with streamablehttp_client(url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    tools = tools_result.tools if hasattr(tools_result, 'tools') else tools_result
                    
                    for tool in tools:
                        schema = {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description or f"Execute {tool.name}",
                                "parameters": getattr(tool, 'inputSchema', {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                })
                            }
                        }
                        schemas[tool.name] = schema
        except Exception as e:
            logger.error(f"Failed to load HTTP schemas: {e}")
        
        return schemas
    
    async def _load_stdio_mcp_schemas(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Load schemas from stdio MCP server."""
        command = config.get('command')
        if not command:
            logger.error("Missing 'command' in stdio MCP config")
            return {}
        
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            logger.error("mcp package not installed. Install with: pip install mcp")
            return {}
        
        schemas = {}
        
        try:
            server_params = StdioServerParameters(
                command=command,
                args=config.get("args", []),
                env=config.get("env", {})
            )
            
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    tools = tools_result.tools if hasattr(tools_result, 'tools') else tools_result
                    
                    for tool in tools:
                        schema = {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description or f"Execute {tool.name}",
                                "parameters": getattr(tool, 'inputSchema', {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                })
                            }
                        }
                        schemas[tool.name] = schema
        except Exception as e:
            logger.error(f"Failed to load stdio schemas: {e}")
        
        return schemas
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the registry.
        
        Returns:
            Dict with registry statistics
        """
        return {
            "total_tools": len(self._tools),
            "active_tools": len(self._status_index[MCPToolStatus.ACTIVE]),
            "failed_tools": len(self._status_index[MCPToolStatus.FAILED]),
            "toolkits": len(self._toolkit_mapping),
            "status_breakdown": {
                status.value: len(tools)
                for status, tools in self._status_index.items()
            }
        }


# === Global Registry Instance ===

_mcp_registry: Optional[MCPRegistry] = None


def get_mcp_registry() -> MCPRegistry:
    """Get the global MCP registry instance (singleton).
    
    Returns:
        MCPRegistry singleton instance
    """
    global _mcp_registry
    if _mcp_registry is None:
        _mcp_registry = MCPRegistry()
    return _mcp_registry
