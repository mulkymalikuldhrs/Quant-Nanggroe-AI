"""Health monitoring for colonies and agents.

This module provides health checking, resource tracking, and monitoring
capabilities for the Multi-Colony Ecosystem.

Components:
    - HealthCheck: Performs health checks on colonies and agents.
    - ResourceTracker: Tracks resource usage across the ecosystem.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckResult(BaseModel):
    """Result of a health check.

    Attributes:
        target_id: ID of the checked entity (colony or agent).
        target_type: Type of the checked entity.
        status: Overall health status.
        checks: Individual check results.
        timestamp: When the check was performed.
        response_time_ms: Check execution time in milliseconds.
        error_message: Error details if any check failed.
    """

    target_id: str
    target_type: str = "colony"
    status: HealthStatus = HealthStatus.UNKNOWN
    checks: dict[str, bool] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    response_time_ms: float = 0.0
    error_message: str | None = None


class ResourceSnapshot(BaseModel):
    """A point-in-time snapshot of resource usage.

    Attributes:
        timestamp: When the snapshot was taken.
        cpu_percent: CPU usage percentage (0-100).
        memory_mb: Memory usage in MB.
        memory_percent: Memory usage percentage (0-100).
        disk_mb: Disk usage in MB.
        network_bytes_sent: Network bytes sent.
        network_bytes_recv: Network bytes received.
        active_agents: Number of active agents.
        active_tasks: Number of active tasks.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_mb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    active_agents: int = 0
    active_tasks: int = 0


class ResourceTracker:
    """Tracks resource usage over time for monitoring and alerting.

    The resource tracker collects periodic snapshots and provides
    methods to query current and historical resource usage.

    Example::

        tracker = ResourceTracker(colony_id="colony-1")
        tracker.record(cpu_percent=45.2, memory_mb=1024.0)
        current = tracker.get_current()
        summary = tracker.get_summary()
    """

    def __init__(
        self,
        colony_id: str,
        max_history: int = 1000,
    ) -> None:
        """Initialize the resource tracker.

        Args:
            colony_id: ID of the colony being tracked.
            max_history: Maximum number of snapshots to retain.
        """
        self._colony_id = colony_id
        self._max_history = max_history
        self._history: list[ResourceSnapshot] = []
        self._log = logger.bind(
            colony_id=colony_id,
            component="resource_tracker",
        )

    def record(
        self,
        cpu_percent: float = 0.0,
        memory_mb: float = 0.0,
        memory_percent: float = 0.0,
        disk_mb: float = 0.0,
        network_bytes_sent: int = 0,
        network_bytes_recv: int = 0,
        active_agents: int = 0,
        active_tasks: int = 0,
    ) -> ResourceSnapshot:
        """Record a resource usage snapshot.

        Args:
            cpu_percent: CPU usage percentage.
            memory_mb: Memory usage in MB.
            memory_percent: Memory usage percentage.
            disk_mb: Disk usage in MB.
            network_bytes_sent: Network bytes sent.
            network_bytes_recv: Network bytes received.
            active_agents: Number of active agents.
            active_tasks: Number of active tasks.

        Returns:
            The recorded snapshot.
        """
        snapshot = ResourceSnapshot(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            disk_mb=disk_mb,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            active_agents=active_agents,
            active_tasks=active_tasks,
        )

        self._history.append(snapshot)

        # Trim to max history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        return snapshot

    def get_current(self) -> ResourceSnapshot | None:
        """Get the most recent resource snapshot.

        Returns:
            The latest snapshot, or None if no snapshots recorded.
        """
        return self._history[-1] if self._history else None

    def get_history(
        self,
        limit: int | None = None,
    ) -> list[ResourceSnapshot]:
        """Get historical resource snapshots.

        Args:
            limit: Maximum number of snapshots to return.

        Returns:
            A list of snapshots, newest first.
        """
        history = list(reversed(self._history))
        if limit is not None:
            history = history[:limit]
        return history

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of resource usage statistics.

        Returns:
            A dictionary with average, peak, and current metrics.
        """
        if not self._history:
            return {"status": "no_data", "colony_id": self._colony_id}

        current = self._history[-1]
        avg_cpu = sum(s.cpu_percent for s in self._history) / len(self._history)
        peak_cpu = max(s.cpu_percent for s in self._history)
        avg_memory = sum(s.memory_mb for s in self._history) / len(self._history)
        peak_memory = max(s.memory_mb for s in self._history)

        return {
            "colony_id": self._colony_id,
            "sample_count": len(self._history),
            "current": {
                "cpu_percent": current.cpu_percent,
                "memory_mb": current.memory_mb,
                "active_agents": current.active_agents,
                "active_tasks": current.active_tasks,
            },
            "averages": {
                "cpu_percent": round(avg_cpu, 2),
                "memory_mb": round(avg_memory, 2),
            },
            "peaks": {
                "cpu_percent": round(peak_cpu, 2),
                "memory_mb": round(peak_memory, 2),
            },
        }

    def clear_history(self) -> None:
        """Clear all historical snapshots."""
        self._history.clear()


class HealthMonitor:
    """Performs health checks on colonies and agents.

    The health monitor runs periodic checks and aggregates results
    to provide an overall health assessment.

    Example::

        monitor = HealthMonitor()
        result = await monitor.check_health("colony-1", checks)
        assert result.status == HealthStatus.HEALTHY
    """

    def __init__(self, resource_tracker: ResourceTracker | None = None) -> None:
        """Initialize the health monitor.

        Args:
            resource_tracker: Optional resource tracker for metrics-based checks.
        """
        self._resource_tracker = resource_tracker
        self._check_history: dict[str, list[HealthCheckResult]] = {}
        self._log = logger.bind(component="health_monitor")

    async def check_health(
        self,
        target_id: str,
        checks: dict[str, callable] | None = None,
        target_type: str = "colony",
    ) -> HealthCheckResult:
        """Perform a health check on a target entity.

        Args:
            target_id: ID of the entity to check.
            checks: Dictionary of check_name -> async check function.
                Each check function should return bool (True = pass).
            target_type: Type of entity ('colony' or 'agent').

        Returns:
            The health check result.
        """
        start_time = time.monotonic()
        result = HealthCheckResult(
            target_id=target_id,
            target_type=target_type,
        )

        # Default checks if none provided
        if checks is None:
            checks = {
                "liveness": self._check_liveness,
                "responsiveness": self._check_responsiveness,
            }

        for check_name, check_fn in checks.items():
            try:
                if asyncio.iscoroutinefunction(check_fn):
                    passed = await check_fn(target_id)
                else:
                    passed = check_fn(target_id)
                result.checks[check_name] = bool(passed)
            except Exception as exc:
                result.checks[check_name] = False
                result.error_message = str(exc)
                self._log.warning(
                    "health_check_failed",
                    target_id=target_id,
                    check=check_name,
                    error=str(exc),
                )

        # Determine overall status
        if not result.checks:
            result.status = HealthStatus.UNKNOWN
        elif all(result.checks.values()):
            result.status = HealthStatus.HEALTHY
        elif any(result.checks.values()):
            result.status = HealthStatus.DEGRADED
        else:
            result.status = HealthStatus.UNHEALTHY

        result.response_time_ms = (time.monotonic() - start_time) * 1000

        # Record in history
        if target_id not in self._check_history:
            self._check_history[target_id] = []
        self._check_history[target_id].append(result)

        self._log.info(
            "health_check_completed",
            target_id=target_id,
            status=result.status.value,
            checks=result.checks,
        )

        return result

    async def check_liveness(self, target_id: str) -> HealthCheckResult:
        """Quick liveness check for a target.

        Args:
            target_id: ID of the entity to check.

        Returns:
            A liveness health check result.
        """
        return await self.check_health(
            target_id,
            checks={"liveness": self._check_liveness},
            target_type="colony",
        )

    def resource_usage(self, target_id: str) -> dict[str, Any]:
        """Get resource usage for a tracked entity.

        Args:
            target_id: ID of the entity.

        Returns:
            Resource usage summary, or empty dict if not tracked.
        """
        if self._resource_tracker is None:
            return {}

        summary = self._resource_tracker.get_summary()
        return summary

    def agent_count(self, target_id: str) -> int:
        """Get the number of active agents for a target.

        Args:
            target_id: ID of the colony.

        Returns:
            Number of active agents from the latest snapshot.
        """
        if self._resource_tracker is None:
            return 0

        current = self._resource_tracker.get_current()
        return current.active_agents if current else 0

    def get_check_history(
        self,
        target_id: str,
        limit: int | None = None,
    ) -> list[HealthCheckResult]:
        """Get health check history for a target.

        Args:
            target_id: ID of the entity.
            limit: Maximum number of results to return.

        Returns:
            A list of health check results, newest first.
        """
        history = list(reversed(self._check_history.get(target_id, [])))
        if limit is not None:
            history = history[:limit]
        return history

    async def _check_liveness(self, target_id: str) -> bool:
        """Default liveness check implementation.

        Args:
            target_id: ID of the entity to check.

        Returns:
            True if the entity is alive.
        """
        # Stub: in production, this would ping the colony/agent
        await asyncio.sleep(0)
        return True

    async def _check_responsiveness(self, target_id: str) -> bool:
        """Default responsiveness check implementation.

        Args:
            target_id: ID of the entity to check.

        Returns:
            True if the entity responds within timeout.
        """
        # Stub: in production, this would measure response time
        await asyncio.sleep(0)
        return True
