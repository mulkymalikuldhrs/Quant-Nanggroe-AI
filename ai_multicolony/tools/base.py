"""MCPTool abstract base class for all tools in the AI-MultiColony ecosystem.

Defines the contract every tool must implement: name, category, autonomy level,
schemas, execution, health checking, rate limiting, and error codes.
"""

from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class ToolHealth(BaseModel):
    """Health status of a tool."""
    model_config = ConfigDict(frozen=False)

    healthy: bool = True
    last_check: float = Field(default_factory=time.time)
    consecutive_failures: int = 0
    total_calls: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    message: str = "OK"


class RateLimitConfig(BaseModel):
    """Rate limiting configuration for a tool."""
    model_config = ConfigDict(frozen=False)

    calls_per_minute: int = 60
    burst: int = 10
    per_agent_limit: int = 120
    cooldown_seconds: float = 1.0


class MCPTool(ABC):
    """Abstract base class for all MCP tools in the AI-MultiColony ecosystem.

    Every tool must implement:
      - name()           -> dotted identifier e.g. 'browser.navigate'
      - category()       -> group for discovery e.g. 'browser'
      - autonomy_level() -> minimum autonomy 0-4 required
      - input_schema()   -> JSON Schema describing accepted params
      - output_schema()  -> JSON Schema describing returned data
      - execute()        -> async execution body

    Optionally override:
      - health_check()   -> runtime liveness probe
      - rate_limit()     -> per-tool rate-limit config
      - error_codes()    -> domain-specific error codes
    """

    # ── Constructor ──────────────────────────────────────────────

    def __init__(self) -> None:
        self._health = ToolHealth()
        self._rate_limit_config = self.rate_limit()
        self._call_timestamps: List[float] = []
        self._agent_timestamps: Dict[str, List[float]] = {}
        self._start_times: Dict[str, float] = {}  # call_id -> start timestamp
        self._total_latency_ms: float = 0.0

    # ── Abstract interface ───────────────────────────────────────

    @abstractmethod
    def name(self) -> str:
        """Unique dotted identifier for this tool (e.g. 'browser.navigate')."""
        ...

    @abstractmethod
    def category(self) -> str:
        """Tool category used for discovery grouping (e.g. 'browser')."""
        ...

    @abstractmethod
    def autonomy_level(self) -> int:
        """Minimum autonomy level required to invoke this tool (0-4).

        L0 = read-only / informational
        L1 = safe operations (read files, search)
        L2 = moderate side-effects (write files, shell exec)
        L3 = sensitive operations (credential access, docker destroy)
        L4 = destructive / irreversible operations
        """
        ...

    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema describing the parameters this tool accepts."""
        ...

    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """JSON Schema describing the data this tool returns."""
        ...

    @abstractmethod
    async def execute(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the given *params* and agent *context*.

        Parameters
        ----------
        params : dict
            Validated input parameters conforming to ``input_schema``.
        context : dict
            Agent context including at least ``agent_id`` and
            ``autonomy_level``.  May also contain ``colony_id``,
            ``session_id``, etc.

        Returns
        -------
        dict
            Result payload conforming to ``output_schema``.
        """
        ...

    # ── Overridable hooks ────────────────────────────────────────

    def health_check(self) -> bool:
        """Return ``True`` if the tool is healthy and ready to serve requests.

        The default implementation tracks consecutive failures: after
        ``_max_consecutive_failures`` the tool reports unhealthy until
        ``record_call(True)`` resets the counter.
        """
        return self._health.healthy

    def rate_limit(self) -> RateLimitConfig:
        """Per-tool rate-limit configuration.

        Override to customise.  The default allows 60 calls/minute with
        a burst of 10.
        """
        return RateLimitConfig()

    def error_codes(self) -> List[Dict[str, Any]]:
        """Return a list of domain-specific error codes this tool may produce.

        Each entry is a dict with at least ``code`` (int) and ``message``
        (str).
        """
        return []

    # ── Call recording / metrics ─────────────────────────────────

    def record_call(self, success: bool, latency_ms: float = 0.0) -> None:
        """Record the outcome of a tool invocation for health & metrics."""
        self._health.total_calls += 1
        self._health.avg_latency_ms = (
            (self._health.avg_latency_ms * (self._health.total_calls - 1) + latency_ms)
            / self._health.total_calls
        )
        if success:
            self._health.consecutive_failures = 0
            self._health.total_errors = self._health.total_errors  # unchanged
        else:
            self._health.consecutive_failures += 1
            self._health.total_errors += 1
            if self._health.consecutive_failures >= self._max_consecutive_failures:
                self._health.healthy = False
                self._health.message = (
                    f"Unhealthy: {self._health.consecutive_failures} consecutive failures"
                )
                logger.warning(
                    "Tool %s marked unhealthy after %d consecutive failures",
                    self.name(),
                    self._health.consecutive_failures,
                )
        self._health.last_check = time.time()

    @property
    def _max_consecutive_failures(self) -> int:
        """Number of consecutive failures before the tool is marked unhealthy."""
        return 5

    # ── Rate-limit enforcement ───────────────────────────────────

    def check_rate_limit(self, agent_id: str = "") -> bool:
        """Return ``True`` if the call is allowed under the rate limit.

        Uses a sliding-window algorithm for global and per-agent limits.
        """
        now = time.time()
        cfg = self._rate_limit_config

        # Global sliding window
        window_start = now - 60.0
        self._call_timestamps = [
            t for t in self._call_timestamps if t > window_start
        ]
        if len(self._call_timestamps) >= cfg.calls_per_minute:
            return False

        # Per-agent sliding window
        if agent_id:
            if agent_id not in self._agent_timestamps:
                self._agent_timestamps[agent_id] = []
            agent_ts = self._agent_timestamps[agent_id]
            agent_ts[:] = [t for t in agent_ts if t > window_start]
            if len(agent_ts) >= cfg.per_agent_limit:
                return False
            agent_ts.append(now)

        self._call_timestamps.append(now)
        return True

    # ── Convenience properties ───────────────────────────────────

    @property
    def stats(self) -> Dict[str, Any]:
        """Runtime statistics for this tool."""
        return {
            "name": self.name(),
            "category": self.category(),
            "autonomy_level": self.autonomy_level(),
            "health": self._health.model_dump(),
            "rate_limit": self._rate_limit_config.model_dump(),
        }

    def describe(self) -> Dict[str, Any]:
        """Full tool description for MCP ``tools/describe`` responses."""
        return {
            "name": self.name(),
            "category": self.category(),
            "autonomy_level": self.autonomy_level(),
            "input_schema": self.input_schema(),
            "output_schema": self.output_schema(),
            "rate_limit": self._rate_limit_config.model_dump(),
            "error_codes": self.error_codes(),
            "health": self._health.model_dump(),
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name()} level=L{self.autonomy_level()}>"
