"""
AgentPress - Agent framework extracted from suna and adapted for Quant-Nanggroe-AI.

Core components:
- Tool: Base class for creating tools with schema registration and result handling
- ToolRegistry: Central registry for managing and discovering tools
- XMLToolParser: Parse XML-style tool calls from LLM responses
- NativeToolParser: Parse OpenAI-style native tool calls from LLM responses
- MCPRegistry: Registry for MCP (Model Context Protocol) tool discovery and management
- MCPClient: Standalone MCP client for connecting to MCP servers
- ContextManager: Token counting and conversation context compression
- ErrorProcessor: Standardized error handling for tool execution
- AgentLoop: Main agent execution loop with tool calling and auto-continuation
- ToolExecutor: Unified tool execution with timeout, retry, and error handling
- ToolDiscovery: Automatic tool discovery and registration
- AgentMemory: Unified memory system with embedding, retrieval, and prompt formatting
- SandboxPool: Pool of sandbox instances for agent tool execution
- TradingSandbox: Specialized sandbox for trading strategy validation
"""

from quant_nanggroe_ai.agents.agentpress.tool import (
    Tool,
    ToolResult,
    ToolSchema,
    ToolMetadata,
    MethodMetadata,
    SchemaType,
    openapi_schema,
    tool_metadata,
    method_metadata,
)
from quant_nanggroe_ai.agents.agentpress.tool_registry import ToolRegistry
from quant_nanggroe_ai.agents.agentpress.xml_tool_parser import (
    XMLToolCall,
    parse_xml_tool_calls_to_objects,
    strip_xml_tool_calls,
    extract_xml_chunks,
    parse_xml_tool_calls_with_ids,
    parse_xml_tool_calls,
)
from quant_nanggroe_ai.agents.agentpress.native_tool_parser import (
    extract_tool_call_chunk_data,
    is_tool_call_complete,
    parse_native_tool_call_arguments,
    convert_to_exec_tool_call,
    convert_buffer_to_complete_tool_calls,
    convert_to_unified_tool_call_format,
    convert_buffer_to_metadata_tool_calls,
)
from quant_nanggroe_ai.agents.agentpress.mcp_registry import (
    MCPRegistry,
    MCPToolInfo,
    MCPToolStatus,
    MCPExecutionContext,
    get_mcp_registry,
)
from quant_nanggroe_ai.agents.agentpress.mcp_client import (
    MCPClient,
    MCPServerConfig,
    MCPTransport,
    MCPConnectionStatus,
    MCPToolSchema,
)
from quant_nanggroe_ai.agents.agentpress.context_manager import ContextManager
from quant_nanggroe_ai.agents.agentpress.error_processor import ErrorProcessor
from quant_nanggroe_ai.agents.agentpress.loop import (
    AgentLoop,
    AgentConfig,
    AgentStatus,
    LoopStats,
    TerminationReason,
)
from quant_nanggroe_ai.agents.agentpress.tools import (
    ToolExecutor,
    ToolDiscovery,
    ToolExecutionError,
)
from quant_nanggroe_ai.agents.agentpress.memory import (
    AgentMemory,
    MemoryType,
    MemoryEntry,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
    HashEmbeddingProvider,
)
from quant_nanggroe_ai.agents.agentpress.sandbox import (
    SandboxPool,
    TradingSandbox,
)

__all__ = [
    # Tool base
    "Tool",
    "ToolResult",
    "ToolSchema",
    "ToolMetadata",
    "MethodMetadata",
    "SchemaType",
    "openapi_schema",
    "tool_metadata",
    "method_metadata",
    # Tool registry
    "ToolRegistry",
    # XML tool parser
    "XMLToolCall",
    "parse_xml_tool_calls_to_objects",
    "strip_xml_tool_calls",
    "extract_xml_chunks",
    "parse_xml_tool_calls_with_ids",
    "parse_xml_tool_calls",
    # Native tool parser
    "extract_tool_call_chunk_data",
    "is_tool_call_complete",
    "parse_native_tool_call_arguments",
    "convert_to_exec_tool_call",
    "convert_buffer_to_complete_tool_calls",
    "convert_to_unified_tool_call_format",
    "convert_buffer_to_metadata_tool_calls",
    # MCP registry
    "MCPRegistry",
    "MCPToolInfo",
    "MCPToolStatus",
    "MCPExecutionContext",
    "get_mcp_registry",
    # MCP client
    "MCPClient",
    "MCPServerConfig",
    "MCPTransport",
    "MCPConnectionStatus",
    "MCPToolSchema",
    # Context management
    "ContextManager",
    # Error processing
    "ErrorProcessor",
    # Agent loop
    "AgentLoop",
    "AgentConfig",
    "AgentStatus",
    "LoopStats",
    "TerminationReason",
    # Tool execution
    "ToolExecutor",
    "ToolDiscovery",
    "ToolExecutionError",
    # Memory
    "AgentMemory",
    "MemoryType",
    "MemoryEntry",
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "LocalEmbeddingProvider",
    "HashEmbeddingProvider",
    # Sandbox
    "SandboxPool",
    "TradingSandbox",
]
