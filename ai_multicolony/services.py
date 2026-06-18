"""Service singletons for the AI-MultiColony ecosystem.

Provides lazy-initialised singletons for every core service:

1. ``get_agent_registry()``   – agent lifecycle management
2. ``get_tool_registry()``    – tool registration and lookup
3. ``get_mcp_server()``       – MCP protocol server
4. ``get_memory_manager()``   – multi-tier memory system
5. ``get_colony_manager()``   – colony lifecycle and coordination
6. ``get_security_analyzer()``– code/dependency security analysis
7. ``get_audit_logger()``     – append-only audit trail
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Singleton caches ──────────────────────────────────────────────────────────

_agent_registry: Optional[object] = None
_tool_registry: Optional[object] = None
_mcp_server: Optional[object] = None
_memory_manager: Optional[object] = None
_colony_manager: Optional[object] = None
_security_analyzer: Optional[object] = None
_audit_logger: Optional[object] = None


def get_agent_registry() -> object:
    """Return the singleton AgentRegistry (lazy-initialised).

    The AgentRegistry manages agent creation, lookup, and lifecycle.
    """
    global _agent_registry
    if _agent_registry is None:
        from .agents import AgentRegistry, EventBus
        event_bus = EventBus()
        _agent_registry = AgentRegistry(event_bus=event_bus)
        logger.info("AgentRegistry singleton created")
    return _agent_registry


def get_tool_registry() -> object:
    """Return the singleton tool registry (lazy-initialised).

    Wraps the MCP server's tool map with a convenience interface.
    """
    global _tool_registry
    if _tool_registry is None:
        from .mcp import MCPServer
        server = get_mcp_server()
        _tool_registry = _ToolRegistryAdapter(server)
        logger.info("ToolRegistry singleton created")
    return _tool_registry


def get_mcp_server() -> object:
    """Return the singleton MCPServer (lazy-initialised)."""
    global _mcp_server
    if _mcp_server is None:
        from .mcp import MCPServer, PermissionEngine
        perm_engine = _get_permission_engine()
        _mcp_server = MCPServer(permission_engine=perm_engine)
        logger.info("MCPServer singleton created")
    return _mcp_server


def get_memory_manager() -> object:
    """Return the singleton MemoryManager (lazy-initialised)."""
    global _memory_manager
    if _memory_manager is None:
        from .memory import MemoryManager
        _memory_manager = MemoryManager()
        logger.info("MemoryManager singleton created")
    return _memory_manager


def get_colony_manager() -> object:
    """Return the singleton ColonyManager (lazy-initialised)."""
    global _colony_manager
    if _colony_manager is None:
        from .colony import ColonyManager
        _colony_manager = ColonyManager()
        logger.info("ColonyManager singleton created")
    return _colony_manager


def get_security_analyzer() -> object:
    """Return the singleton SecurityAnalyzer (lazy-initialised)."""
    global _security_analyzer
    if _security_analyzer is None:
        from .security import SecurityAnalyzer
        _security_analyzer = SecurityAnalyzer()
        logger.info("SecurityAnalyzer singleton created")
    return _security_analyzer


def get_audit_logger() -> object:
    """Return the singleton AuditTrail (lazy-initialised)."""
    global _audit_logger
    if _audit_logger is None:
        from .security import AuditTrail
        from .config import get_settings
        settings = get_settings()
        _audit_logger = AuditTrail(
            level=settings.security.audit_level,
            storage=settings.security.audit_storage,
            file_path=settings.security.audit_file_path,
            retention_days=settings.security.audit_retention_days,
        )
        logger.info("AuditTrail singleton created")
    return _audit_logger


# ── Internal helpers ──────────────────────────────────────────────────────────

_permission_engine: Optional[object] = None


def _get_permission_engine() -> object:
    """Return a shared PermissionEngine (used by MCP and security)."""
    global _permission_engine
    if _permission_engine is None:
        from .security import PermissionEngine
        _permission_engine = PermissionEngine(audit_trail=get_audit_logger())
    return _permission_engine


class _ToolRegistryAdapter:
    """Adapter that provides a registry-like interface over the MCP server's tools."""

    def __init__(self, mcp_server: object):
        self._server = mcp_server

    def register(self, tool: object) -> None:
        """Register a tool with the MCP server."""
        if hasattr(self._server, "register_tool"):
            self._server.register_tool(tool)

    def get(self, name: str) -> Optional[object]:
        """Look up a tool by name."""
        if hasattr(self._server, "_tools"):
            return self._server._tools.get(name)
        return None

    def list_tools(self) -> list:
        """List all registered tools."""
        if hasattr(self._server, "_tools"):
            return list(self._server._tools.values())
        return []

    @property
    def tool_count(self) -> int:
        return len(self.list_tools())


# ── Reset (for testing) ──────────────────────────────────────────────────────


def reset_services() -> None:
    """Reset all singleton instances (useful for tests)."""
    global _agent_registry, _tool_registry, _mcp_server
    global _memory_manager, _colony_manager, _security_analyzer, _audit_logger
    global _permission_engine

    _agent_registry = None
    _tool_registry = None
    _mcp_server = None
    _memory_manager = None
    _colony_manager = None
    _security_analyzer = None
    _audit_logger = None
    _permission_engine = None
    logger.info("All service singletons reset")
