"""MCP Tool layer for AI-MultiColony.

Provides the abstract base class (:class:`MCPTool`) and all concrete tool
implementations, plus the central :class:`ToolRegistry` for discovery and
permission-aware dispatch.
"""

from .base import MCPTool, RateLimitConfig, ToolHealth
from .shell import ShellTool
from .file import FileTool
from .browser import BrowserTool
from .search import SearchTool
from .code import CodeTool
from .docker import DockerTool
from .voice import VoiceTool
from .memory import MemoryTool
from .channel import ChannelTool
from .registry import ToolRegistry

# Backward-compat alias
from .mcp import MCPToolBase  # noqa: F401

__all__ = [
    "MCPTool",
    "MCPToolBase",
    "RateLimitConfig",
    "ToolHealth",
    "ShellTool",
    "FileTool",
    "BrowserTool",
    "SearchTool",
    "CodeTool",
    "DockerTool",
    "VoiceTool",
    "MemoryTool",
    "ChannelTool",
    "ToolRegistry",
]
