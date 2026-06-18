"""ToolRegistry – central registry for tool discovery, permission-aware
dispatch, rate limiting, circuit breaking, and audit logging.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field, ConfigDict

from .base import MCPTool

logger = logging.getLogger(__name__)


# ── Pydantic models ──────────────────────────────────────────────

class CircuitBreakerConfig(BaseModel):
    """Configuration for per-tool circuit breaker."""
    model_config = ConfigDict(frozen=False)

    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    half_open_max_calls: int = 3


class CircuitBreakerState(BaseModel):
    """Runtime state of a circuit breaker."""
    model_config = ConfigDict(frozen=False)

    state: str = "closed"  # closed | open | half_open
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = Field(default_factory=time.time)

    def can_execute(self, config: CircuitBreakerConfig) -> bool:
        """Check if a call is allowed through the circuit breaker."""
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.last_failure_time is None:
                return False
            elapsed = time.time() - self.last_failure_time
            if elapsed >= config.recovery_timeout_seconds:
                self.state = "half_open"
                self.last_state_change = time.time()
                return True
            return False
        if self.state == "half_open":
            return self.success_count < config.half_open_max_calls
        return False

    def record_success(self, config: CircuitBreakerConfig) -> None:
        self.success_count += 1
        if self.state == "half_open" and self.success_count >= config.half_open_max_calls:
            self.state = "closed"
            self.failure_count = 0
            self.last_state_change = time.time()

    def record_failure(self, config: CircuitBreakerConfig) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == "half_open":
            self.state = "open"
            self.last_state_change = time.time()
        elif self.failure_count >= config.failure_threshold:
            self.state = "open"
            self.last_state_change = time.time()


class AuditEntry(BaseModel):
    """Audit log entry for a tool invocation."""
    model_config = ConfigDict(frozen=False)

    audit_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    tool_name: str = ""
    action: str = ""
    agent_id: str = ""
    colony_id: str = ""
    autonomy_level: int = 0
    granted: bool = False
    success: Optional[bool] = None
    duration_ms: float = 0.0
    error: str = ""


# ── Registry ─────────────────────────────────────────────────────

class ToolRegistry:
    """Central registry for MCP tools with discovery, permission checking,
    rate limiting, circuit breaking, and audit logging.

    Usage
    -----
    >>> registry = ToolRegistry()
    >>> registry.register(ShellTool())
    >>> tools = registry.list_tools(category="compute")
    >>> result = await registry.call("shell.execute", {"command": "ls"}, context)
    """

    def __init__(
        self,
        cb_config: Optional[CircuitBreakerConfig] = None,
    ) -> None:
        self._tools: Dict[str, MCPTool] = {}
        self._categories: Dict[str, Set[str]] = {}  # category -> set of tool names
        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self._cb_config = cb_config or CircuitBreakerConfig()
        self._audit_log: List[AuditEntry] = []
        self._max_audit_entries: int = 10_000

    # ── Registration ─────────────────────────────────────────────

    def register(self, tool: MCPTool) -> None:
        """Register a tool instance with the registry."""
        name = tool.name()
        if name in self._tools:
            logger.warning("Tool %s already registered; replacing", name)

        self._tools[name] = tool
        cat = tool.category()
        if cat not in self._categories:
            self._categories[cat] = set()
        self._categories[cat].add(name)
        self._circuit_breakers[name] = CircuitBreakerState()

        logger.info("Registered tool: %s (category=%s, autonomy=L%d)", name, cat, tool.autonomy_level())

    def unregister(self, tool_name: str) -> bool:
        """Remove a tool from the registry."""
        if tool_name not in self._tools:
            return False

        tool = self._tools.pop(tool_name)
        cat = tool.category()
        if cat in self._categories:
            self._categories[cat].discard(tool_name)
            if not self._categories[cat]:
                del self._categories[cat]

        self._circuit_breakers.pop(tool_name, None)
        logger.info("Unregistered tool: %s", tool_name)
        return True

    # ── Discovery ────────────────────────────────────────────────

    def get(self, tool_name: str) -> Optional[MCPTool]:
        """Get a tool by name, or None if not found."""
        return self._tools.get(tool_name)

    def list_tools(
        self,
        category: Optional[str] = None,
        min_autonomy: Optional[int] = None,
        max_autonomy: Optional[int] = None,
        healthy_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """List registered tools with optional filtering."""
        tools = []
        for name, tool in self._tools.items():
            # Category filter
            if category and tool.category() != category:
                continue
            # Autonomy filter
            al = tool.autonomy_level()
            if min_autonomy is not None and al < min_autonomy:
                continue
            if max_autonomy is not None and al > max_autonomy:
                continue
            # Health filter
            if healthy_only and not tool.health_check():
                continue

            tools.append(tool.describe())

        return tools

    def list_categories(self) -> List[str]:
        """List all tool categories."""
        return sorted(self._categories.keys())

    def list_tools_by_category(self) -> Dict[str, List[str]]:
        """Get a mapping of category → list of tool names."""
        return {cat: sorted(names) for cat, names in self._categories.items()}

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    # ── Permission checking ──────────────────────────────────────

    def check_permission(self, tool_name: str, autonomy_level: int) -> Dict[str, Any]:
        """Check if an agent with the given autonomy level can use a tool.

        Returns a dict with ``granted`` (bool) and ``reason`` (str).
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return {"granted": False, "reason": f"Tool not found: {tool_name}"}

        required = tool.autonomy_level()
        if autonomy_level >= required:
            return {"granted": True, "reason": ""}

        return {
            "granted": False,
            "reason": f"Requires L{required}, agent has L{autonomy_level}",
            "required_level": required,
            "current_level": autonomy_level,
            "escalation_available": True,
        }

    # ── Circuit breaker ──────────────────────────────────────────

    def circuit_breaker_state(self, tool_name: str) -> Optional[str]:
        """Get the circuit breaker state for a tool."""
        cb = self._circuit_breakers.get(tool_name)
        return cb.state if cb else None

    def reset_circuit_breaker(self, tool_name: str) -> bool:
        """Force-reset a tool's circuit breaker to closed."""
        cb = self._circuit_breakers.get(tool_name)
        if cb:
            cb.state = "closed"
            cb.failure_count = 0
            cb.success_count = 0
            cb.last_failure_time = None
            cb.last_state_change = time.time()
            return True
        return False

    # ── Call (dispatch) ──────────────────────────────────────────

    async def call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch a call to a registered tool with full safety checks.

        Checks (in order):
          1. Tool exists
          2. Permission (autonomy level)
          3. Rate limit
          4. Circuit breaker
          5. Execute

        All outcomes are audit-logged.
        """
        agent_id = context.get("agent_id", "")
        colony_id = context.get("colony_id", "")
        autonomy = context.get("autonomy_level", 0)
        audit = AuditEntry(
            tool_name=tool_name,
            agent_id=agent_id,
            colony_id=colony_id,
            autonomy_level=autonomy,
        )

        # 1. Tool exists?
        tool = self._tools.get(tool_name)
        if tool is None:
            audit.granted = False
            audit.error = f"Tool not found: {tool_name}"
            self._log_audit(audit)
            return {"success": False, "error": audit.error, "error_code": -32601}

        # 2. Permission check
        perm = self.check_permission(tool_name, autonomy)
        if not perm["granted"]:
            audit.granted = False
            audit.error = perm["reason"]
            self._log_audit(audit)
            return {
                "success": False,
                "error": perm["reason"],
                "error_code": -32001,
                "required_level": perm.get("required_level"),
                "current_level": perm.get("current_level"),
            }

        audit.granted = True

        # 3. Rate limit
        if not tool.check_rate_limit(agent_id):
            audit.error = "Rate limited"
            audit.success = False
            self._log_audit(audit)
            return {"success": False, "error": "Rate limited", "error_code": -32002}

        # 4. Circuit breaker
        cb = self._circuit_breakers.get(tool_name)
        if cb and not cb.can_execute(self._cb_config):
            audit.error = f"Tool unavailable (circuit breaker open)"
            audit.success = False
            self._log_audit(audit)
            return {"success": False, "error": audit.error, "error_code": -32003}

        # 5. Execute
        start = time.monotonic()
        try:
            result = await tool.execute(params, context)
            duration = (time.monotonic() - start) * 1000
            audit.success = True
            audit.duration_ms = duration
            if cb:
                cb.record_success(self._cb_config)
            self._log_audit(audit)
            return result

        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            audit.success = False
            audit.duration_ms = duration
            audit.error = str(exc)
            if cb:
                cb.record_failure(self._cb_config)
            self._log_audit(audit)
            return {"success": False, "error": str(exc), "error_code": -32603}

    # ── Audit log ────────────────────────────────────────────────

    def _log_audit(self, entry: AuditEntry) -> None:
        self._audit_log.append(entry)
        # Trim if too large
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]

    def get_audit_log(
        self,
        tool_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        granted: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query the audit log with optional filters."""
        entries = self._audit_log

        if tool_name:
            entries = [e for e in entries if e.tool_name == tool_name]
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        if granted is not None:
            entries = [e for e in entries if e.granted == granted]

        return [e.model_dump() for e in entries[-limit:]]

    # ── Health / diagnostics ─────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """Run health checks on all registered tools."""
        results = {}
        for name, tool in self._tools.items():
            healthy = tool.health_check()
            cb = self._circuit_breakers.get(name)
            results[name] = {
                "healthy": healthy,
                "circuit_breaker": cb.state if cb else "unknown",
                "stats": tool.stats,
            }
        return {
            "total_tools": len(self._tools),
            "healthy_tools": sum(1 for r in results.values() if r["healthy"]),
            "open_circuits": sum(1 for r in results.values() if r["circuit_breaker"] == "open"),
            "details": results,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate statistics across all tools."""
        return {
            "tool_count": len(self._tools),
            "categories": {cat: len(names) for cat, names in self._categories.items()},
            "audit_entries": len(self._audit_log),
            "circuit_breakers": {
                name: cb.state for name, cb in self._circuit_breakers.items()
            },
        }
