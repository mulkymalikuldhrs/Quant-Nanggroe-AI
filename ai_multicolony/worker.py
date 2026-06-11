"""Async worker – background task processing loops.

Runs 5 continuous async loops:

1. **heartbeat_loop**        – 30s agent check-ins
2. **task_scheduler_loop**   – task distribution to agents
3. **health_monitor_loop**   – agent health scoring
4. **memory_compaction_loop** – context compaction
5. **audit_flush_loop**      – audit log persistence
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .config import get_settings

logger = logging.getLogger(__name__)


class AsyncWorker:
    """Background task worker with 5 async processing loops.

    The worker runs continuously while ``running`` is True, managing:
    * Agent heartbeats and liveness tracking
    * Task scheduling and distribution
    * Health score computation
    * Memory compaction
    * Audit log flushing

    Usage::

        worker = AsyncWorker()
        await worker.start()
        # ... run the system ...
        await worker.stop()
    """

    def __init__(
        self,
        agent_registry: Any = None,
        colony_manager: Any = None,
        task_scheduler: Any = None,
        memory_manager: Any = None,
        audit_trail: Any = None,
    ):
        self.agent_registry = agent_registry
        self.colony_manager = colony_manager
        self.task_scheduler = task_scheduler
        self.memory_manager = memory_manager
        self.audit_trail = audit_trail

        self.running: bool = False
        self._tasks: List[asyncio.Task] = []
        self._stats: Dict[str, Dict[str, Any]] = {
            "heartbeat": {"runs": 0, "last_run": None},
            "scheduler": {"runs": 0, "last_run": None},
            "health": {"runs": 0, "last_run": None},
            "compaction": {"runs": 0, "last_run": None},
            "audit_flush": {"runs": 0, "last_run": None},
        }

        # Load intervals from settings
        settings = get_settings()
        self.heartbeat_interval_s: int = settings.colony.heartbeat_interval_ms // 1000 or 30
        self.scheduler_interval_s: float = 0.5
        self.health_interval_s: int = settings.colony.health_check_interval_ms // 1000 or 60
        self.compaction_interval_s: int = settings.memory.compaction_interval_s or 300
        self.audit_flush_interval_s: int = settings.security.audit_flush_interval_s or 10

    # ── Start / Stop ───────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start all background loops."""
        if self.running:
            logger.warning("AsyncWorker already running")
            return

        self.running = True
        self._tasks = [
            asyncio.create_task(self.heartbeat_loop(), name="heartbeat_loop"),
            asyncio.create_task(self.task_scheduler_loop(), name="task_scheduler_loop"),
            asyncio.create_task(self.health_monitor_loop(), name="health_monitor_loop"),
            asyncio.create_task(self.memory_compaction_loop(), name="memory_compaction_loop"),
            asyncio.create_task(self.audit_flush_loop(), name="audit_flush_loop"),
        ]
        logger.info(
            "AsyncWorker started with 5 loops (heartbeat=%ds, scheduler=%.1fs, health=%ds, compaction=%ds, audit=%ds)",
            self.heartbeat_interval_s,
            self.scheduler_interval_s,
            self.health_interval_s,
            self.compaction_interval_s,
            self.audit_flush_interval_s,
        )

    async def stop(self) -> None:
        """Stop all background loops."""
        self.running = False
        for task in self._tasks:
            task.cancel()
        # Wait for cancellation
        results = await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("AsyncWorker stopped")

    # ── Loop 1: Heartbeat ──────────────────────────────────────────────────

    async def heartbeat_loop(self) -> None:
        """Periodically check agent heartbeats (30s default).

        Detects agents that have missed their heartbeat window
        and marks them as unhealthy or suspended.
        """
        while self.running:
            try:
                await self._do_heartbeat()
                self._stats["heartbeat"]["runs"] += 1
                self._stats["heartbeat"]["last_run"] = datetime.now(timezone.utc).isoformat()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Heartbeat loop error: %s", exc)

            await asyncio.sleep(self.heartbeat_interval_s)

    async def _do_heartbeat(self) -> None:
        """Check all registered agents for heartbeat freshness."""
        if not self.agent_registry or not hasattr(self.agent_registry, "_agents"):
            return

        now = datetime.now(timezone.utc)
        timeout_delta = __import__("datetime").timedelta(milliseconds=self.heartbeat_interval_s * 2)

        for agent_id, agent in list(getattr(self.agent_registry, "_agents", {}).items()):
            if not hasattr(agent, "info") or not hasattr(agent.info, "last_heartbeat"):
                continue

            last_hb = agent.info.last_heartbeat
            if last_hb is None:
                continue

            # Check if heartbeat is stale
            if now - last_hb > timeout_delta:
                logger.warning("Agent %s missed heartbeat (last: %s)", agent_id, last_hb.isoformat())
                if hasattr(agent, "info"):
                    agent.info.health_score = max(0.0, agent.info.health_score - 0.1)

    # ── Loop 2: Task Scheduler ────────────────────────────────────────────

    async def task_scheduler_loop(self) -> None:
        """Distribute pending tasks to available agents (0.5s interval).

        Picks the next task from the scheduler's priority queue,
        routes it to an appropriate agent, and starts execution.
        """
        while self.running:
            try:
                await self._do_schedule()
                self._stats["scheduler"]["runs"] += 1
                self._stats["scheduler"]["last_run"] = datetime.now(timezone.utc).isoformat()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Scheduler loop error: %s", exc)

            await asyncio.sleep(self.scheduler_interval_s)

    async def _do_schedule(self) -> None:
        """Pick the next task and route it."""
        if not self.task_scheduler:
            return

        # Check for timeouts
        if hasattr(self.task_scheduler, "check_timeouts"):
            timed_out = self.task_scheduler.check_timeouts()
            for tid in timed_out:
                logger.warning("Task %s timed out", tid)

        # Get next task
        if hasattr(self.task_scheduler, "next_task"):
            task = self.task_scheduler.next_task()
            if task is None:
                return

            # Route to agent
            if hasattr(self.task_scheduler, "route_task"):
                agent_id = self.task_scheduler.route_task(task)
                if agent_id:
                    self.task_scheduler.start_task(task.task_id, agent_id)
                    logger.debug("Task %s routed to agent %s", task.task_id, agent_id)
                else:
                    # No agent available – re-queue
                    logger.debug("No agent available for task %s", task.task_id)

    # ── Loop 3: Health Monitor ────────────────────────────────────────────

    async def health_monitor_loop(self) -> None:
        """Compute health scores for agents and colonies (60s default)."""
        while self.running:
            try:
                await self._do_health_monitor()
                self._stats["health"]["runs"] += 1
                self._stats["health"]["last_run"] = datetime.now(timezone.utc).isoformat()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Health monitor loop error: %s", exc)

            await asyncio.sleep(self.health_interval_s)

    async def _do_health_monitor(self) -> None:
        """Compute colony health scores."""
        if not self.colony_manager:
            return

        if hasattr(self.colony_manager, "compute_all_health"):
            health_map = self.colony_manager.compute_all_health()
            for colony_id, health in health_map.items():
                if health.overall_score < 0.5:
                    logger.warning(
                        "Colony %s unhealthy (score=%.2f): %s",
                        colony_id,
                        health.overall_score,
                        health.issues,
                    )

    # ── Loop 4: Memory Compaction ──────────────────────────────────────────

    async def memory_compaction_loop(self) -> None:
        """Trigger memory compaction when thresholds are exceeded (300s default)."""
        while self.running:
            try:
                await self._do_compaction()
                self._stats["compaction"]["runs"] += 1
                self._stats["compaction"]["last_run"] = datetime.now(timezone.utc).isoformat()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Memory compaction loop error: %s", exc)

            await asyncio.sleep(self.compaction_interval_s)

    async def _do_compaction(self) -> None:
        """Run compaction for agents that exceed the threshold."""
        if not self.memory_manager:
            return

        if hasattr(self.memory_manager, "compact_all"):
            try:
                result = await self.memory_manager.compact_all()
                if result and isinstance(result, dict):
                    compacted = result.get("pages_compacted", 0)
                    if compacted > 0:
                        logger.info("Memory compaction: %d pages compacted", compacted)
            except Exception as exc:
                logger.error("Memory compaction error: %s", exc)

    # ── Loop 5: Audit Flush ────────────────────────────────────────────────

    async def audit_flush_loop(self) -> None:
        """Flush buffered audit entries to persistent storage (10s default)."""
        while self.running:
            try:
                await self._do_audit_flush()
                self._stats["audit_flush"]["runs"] += 1
                self._stats["audit_flush"]["last_run"] = datetime.now(timezone.utc).isoformat()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Audit flush loop error: %s", exc)

            await asyncio.sleep(self.audit_flush_interval_s)

    async def _do_audit_flush(self) -> None:
        """Flush the audit trail."""
        if not self.audit_trail:
            return

        if hasattr(self.audit_trail, "flush"):
            self.audit_trail.flush()

    # ── Status ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return worker statistics."""
        return {
            "running": self.running,
            "loops": dict(self._stats),
            "intervals": {
                "heartbeat_s": self.heartbeat_interval_s,
                "scheduler_s": self.scheduler_interval_s,
                "health_s": self.health_interval_s,
                "compaction_s": self.compaction_interval_s,
                "audit_flush_s": self.audit_flush_interval_s,
            },
        }

    # ── Generic task submission (backwards compatible) ─────────────────────

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    # Legacy interface for simple task submission
    _queue: asyncio.Queue = asyncio.Queue()
    _results: Dict[str, Any] = {}
    _workers: List[asyncio.Task] = []
    max_concurrent: int = 10
    poll_interval: float = 0.1
    _running_flag: bool = False

    async def submit(self, task_id: str, func: Callable, *args: Any, **kwargs: Any) -> str:
        """Submit a one-off async task to the internal queue."""
        await self._queue.put((task_id, func, args, kwargs))
        return task_id

    def get_result(self, task_id: str) -> Optional[Any]:
        """Get the result of a submitted task."""
        return self._results.get(task_id)

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    @property
    def completed_count(self) -> int:
        return len(self._results)
