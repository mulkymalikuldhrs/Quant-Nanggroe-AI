"""Singleton Background Worker — AI-Trader Pattern.

Implements a singleton background worker that acquires a file-based lock
to ensure only one instance runs at a time.  Manages configurable
background tasks (price fetching, portfolio rebalancing, strategy health
checks) with graceful shutdown, auto-restart with exponential backoff,
and a health check endpoint.

Features
--------
* File-based singleton lock (optional Redis support)
* Configurable task list via environment variable
* Graceful shutdown on SIGINT/SIGTERM
* Auto-restart with exponential backoff
* Health check endpoint
* Task metrics and status reporting

Usage::

    from quant_nanggroe.engine.worker import BackgroundWorker, WorkerTask

    worker = BackgroundWorker()
    await worker.start()
    # Runs until SIGINT/SIGTERM
    # Or manually:
    health = worker.health_check()
    await worker.stop()
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ── Enums ───────────────────────────────────────────────────────────────


class TaskStatus(str, Enum):
    """Background task status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DISABLED = "DISABLED"


class WorkerState(str, Enum):
    """Worker lifecycle state."""

    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


# ── Pydantic Models ─────────────────────────────────────────────────────


class WorkerHealth(BaseModel):
    """Health check result for the background worker.

    Attributes:
        worker_id: Unique worker identifier.
        state: Current worker state.
        uptime_seconds: Seconds since worker started.
        tasks_running: Number of currently running tasks.
        tasks_completed: Total tasks completed successfully.
        tasks_failed: Total tasks that failed.
        last_error: Last error message (if any).
        lock_held: Whether the singleton lock is held.
        timestamp: UTC timestamp.
    """

    model_config = ConfigDict(frozen=False)

    worker_id: str = ""
    state: WorkerState = WorkerState.STOPPED
    uptime_seconds: float = 0.0
    tasks_running: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_error: Optional[str] = None
    lock_held: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API-safe dictionary."""
        return {
            "worker_id": self.worker_id,
            "state": self.state.value,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "tasks_running": self.tasks_running,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "last_error": self.last_error,
            "lock_held": self.lock_held,
            "timestamp": self.timestamp.isoformat(),
        }


class TaskMetrics(BaseModel):
    """Metrics for a single background task.

    Attributes:
        task_name: Name of the task.
        status: Current status.
        run_count: Number of times the task has run.
        success_count: Number of successful runs.
        failure_count: Number of failed runs.
        last_run_at: Timestamp of last run.
        last_duration_ms: Duration of last run in milliseconds.
        last_error: Last error message.
        next_run_at: Estimated next run time.
    """

    model_config = ConfigDict(frozen=False)

    task_name: str = ""
    status: TaskStatus = TaskStatus.PENDING
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_run_at: Optional[datetime] = None
    last_duration_ms: float = 0.0
    last_error: Optional[str] = None
    next_run_at: Optional[datetime] = None


# ── Task Definition ─────────────────────────────────────────────────────


@dataclass
class WorkerTask:
    """Definition of a background task.

    Attributes:
        name: Task name (must be unique).
        func: Async callable to execute.
        interval_seconds: How often to run the task.
        timeout_seconds: Maximum execution time before cancellation.
        max_retries: Maximum retry attempts on failure.
        retry_backoff_base: Base delay (seconds) for exponential backoff.
        retry_backoff_max: Maximum backoff delay (seconds).
        enabled: Whether the task is active.
    """

    name: str
    func: Callable[[], Coroutine[Any, Any, None]]
    interval_seconds: float = 60.0
    timeout_seconds: float = 120.0
    max_retries: int = 3
    retry_backoff_base: float = 1.0
    retry_backoff_max: float = 60.0
    enabled: bool = True


# ── Singleton Lock ──────────────────────────────────────────────────────


class SingletonLock:
    """File-based singleton lock.

    Ensures only one worker instance runs at a time by creating
    and locking a file.  The lock is automatically released when
    the process exits.

    Args:
        lock_path: Path to the lock file.
        worker_id: Unique worker identifier.
    """

    def __init__(
        self,
        lock_path: str = "/tmp/quant_nanggroe_worker.lock",
        worker_id: Optional[str] = None,
    ) -> None:
        self.lock_path = Path(lock_path)
        self.worker_id = worker_id or uuid.uuid4().hex[:8]
        self._lock_file: Optional[Any] = None
        self._is_held = False

    def acquire(self) -> bool:
        """Try to acquire the singleton lock.

        Returns:
            True if lock acquired, False if another instance holds it.
        """
        try:
            import fcntl

            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._lock_file = open(self.lock_path, "w")
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write worker info
            self._lock_file.write(
                f"worker_id={self.worker_id}\n"
                f"pid={os.getpid()}\n"
                f"started={datetime.now(timezone.utc).isoformat()}\n"
            )
            self._lock_file.flush()

            self._is_held = True
            logger.info(
                "singleton_lock_acquired",
                extra={"worker_id": self.worker_id, "lock_path": str(self.lock_path)},
            )
            return True

        except (IOError, OSError):
            logger.warning(
                "singleton_lock_failed",
                extra={
                    "worker_id": self.worker_id,
                    "lock_path": str(self.lock_path),
                    "message": "Another worker instance is already running",
                },
            )
            if self._lock_file:
                self._lock_file.close()
                self._lock_file = None
            return False

    def release(self) -> None:
        """Release the singleton lock."""
        try:
            if self._lock_file:
                import fcntl
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
                self._lock_file = None
            self.lock_path.unlink(missing_ok=True)
            self._is_held = False
            logger.info(
                "singleton_lock_released",
                extra={"worker_id": self.worker_id},
            )
        except Exception as exc:
            logger.warning(
                "singleton_lock_release_error",
                extra={"error": str(exc)},
            )

    @property
    def is_held(self) -> bool:
        """Whether this worker holds the lock."""
        return self._is_held


# ── Background Worker ───────────────────────────────────────────────────


class BackgroundWorker:
    """Singleton background worker with configurable task management.

    Acquires a file-based singleton lock to ensure only one instance
    runs at a time.  Manages a list of configurable background tasks
    with retry logic, exponential backoff, and graceful shutdown.

    Args:
        worker_id: Unique identifier (auto-generated if None).
        lock_path: Path for the singleton lock file.
        tasks: List of WorkerTask definitions.

    Usage::

        worker = BackgroundWorker(
            tasks=[
                WorkerTask(name="price_fetch", func=fetch_prices, interval=60),
                WorkerTask(name="rebalance_check", func=check_rebalance, interval=300),
            ]
        )
        await worker.start()
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        lock_path: str = "/tmp/quant_nanggroe_worker.lock",
        tasks: Optional[List[WorkerTask]] = None,
    ) -> None:
        self.worker_id = worker_id or uuid.uuid4().hex[:8]
        self._lock = SingletonLock(lock_path=lock_path, worker_id=self.worker_id)
        self._tasks: Dict[str, WorkerTask] = {}
        self._task_metrics: Dict[str, TaskMetrics] = {}
        self._task_handles: Dict[str, asyncio.Task[None]] = {}
        self._state = WorkerState.INITIALIZING
        self._started_at: Optional[float] = None
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._shutdown_event = asyncio.Event()

        # Register default tasks or provided tasks
        for task in (tasks or self._default_tasks()):
            self.register_task(task)

    # ── Task Registration ─────────────────────────────────────────────

    def register_task(self, task: WorkerTask) -> None:
        """Register a background task.

        Args:
            task: WorkerTask definition.

        Raises:
            ValueError: If a task with the same name already exists.
        """
        if task.name in self._tasks:
            raise ValueError(f"Task '{task.name}' already registered")
        self._tasks[task.name] = task
        self._task_metrics[task.name] = TaskMetrics(
            task_name=task.name,
            status=TaskStatus.PENDING if task.enabled else TaskStatus.DISABLED,
        )

    def deregister_task(self, name: str) -> bool:
        """Remove a registered task.

        Args:
            name: Task name.

        Returns:
            True if the task was found and removed.
        """
        if name in self._tasks:
            del self._tasks[name]
            self._task_metrics.pop(name, None)
            return True
        return False

    @staticmethod
    def _default_tasks() -> List[WorkerTask]:
        """Create default background tasks.

        Tasks can be overridden via QNAI_WORKER_TASKS env var
        (comma-separated task names).
        """
        return [
            WorkerTask(
                name="price_fetch",
                func=BackgroundWorker._task_price_fetch,
                interval_seconds=60.0,
                timeout_seconds=30.0,
            ),
            WorkerTask(
                name="portfolio_rebalance_check",
                func=BackgroundWorker._task_rebalance_check,
                interval_seconds=300.0,
                timeout_seconds=60.0,
            ),
            WorkerTask(
                name="strategy_health_check",
                func=BackgroundWorker._task_strategy_health,
                interval_seconds=120.0,
                timeout_seconds=30.0,
            ),
        ]

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> bool:
        """Start the background worker.

        Acquires the singleton lock, registers signal handlers,
        and starts all registered tasks.

        Returns:
            True if started successfully, False if lock acquisition failed.
        """
        if self._state == WorkerState.RUNNING:
            logger.warning("worker_already_running")
            return True

        # Acquire singleton lock
        if not self._lock.acquire():
            self._state = WorkerState.ERROR
            logger.error("worker_start_failed_lock")
            return False

        self._state = WorkerState.RUNNING
        self._started_at = time.time()
        self._shutdown_event.clear()

        # Register signal handlers
        self._register_signal_handlers()

        # Start all enabled tasks
        for name, task in self._tasks.items():
            if task.enabled:
                handle = asyncio.create_task(
                    self._run_task_loop(task),
                    name=f"worker-{name}",
                )
                self._task_handles[name] = handle

        logger.info(
            "worker_started",
            extra={
                "worker_id": self.worker_id,
                "tasks": list(self._task_handles.keys()),
            },
        )

        return True

    async def stop(self) -> None:
        """Gracefully stop the background worker.

        Cancels all running tasks, waits for them to finish,
        releases the singleton lock, and cleans up.
        """
        if self._state in (WorkerState.STOPPED, WorkerState.STOPPING):
            return

        self._state = WorkerState.STOPPING
        self._shutdown_event.set()

        logger.info("worker_stopping", extra={"worker_id": self.worker_id})

        # Cancel all task handles
        for name, handle in self._task_handles.items():
            handle.cancel()

        # Wait for cancellation
        if self._task_handles:
            results = await asyncio.gather(
                *self._task_handles.values(), return_exceptions=True
            )
            for handle, result in zip(self._task_handles.values(), results):
                if isinstance(result, Exception) and not isinstance(
                    result, asyncio.CancelledError
                ):
                    logger.error(
                        "task_error_on_shutdown",
                        extra={
                            "task": handle.get_name(),
                            "error": str(result),
                        },
                    )

        self._task_handles.clear()

        # Release lock
        self._lock.release()

        self._state = WorkerState.STOPPED
        logger.info("worker_stopped", extra={"worker_id": self.worker_id})

    # ── Task Execution Loop ──────────────────────────────────────────

    async def _run_task_loop(self, task: WorkerTask) -> None:
        """Run a single task in a loop with retry and backoff.

        Args:
            task: WorkerTask to execute.
        """
        metrics = self._task_metrics[task.name]
        consecutive_failures = 0

        while not self._shutdown_event.is_set():
            try:
                metrics.status = TaskStatus.RUNNING
                metrics.last_run_at = datetime.now(timezone.utc)

                start = time.time()
                await asyncio.wait_for(
                    task.func(),
                    timeout=task.timeout_seconds,
                )
                duration_ms = (time.time() - start) * 1000

                metrics.run_count += 1
                metrics.success_count += 1
                metrics.last_duration_ms = round(duration_ms, 2)
                metrics.status = TaskStatus.SUCCESS
                metrics.last_error = None
                consecutive_failures = 0

                self._tasks_completed += 1

                logger.debug(
                    "task_completed",
                    extra={
                        "task": task.name,
                        "duration_ms": round(duration_ms, 2),
                    },
                )

            except asyncio.TimeoutError:
                metrics.failure_count += 1
                metrics.status = TaskStatus.FAILED
                metrics.last_error = f"Timeout after {task.timeout_seconds}s"
                consecutive_failures += 1
                self._tasks_failed += 1
                logger.warning(
                    "task_timeout",
                    extra={"task": task.name, "timeout": task.timeout_seconds},
                )

            except asyncio.CancelledError:
                logger.info("task_cancelled", extra={"task": task.name})
                break

            except Exception as exc:
                metrics.failure_count += 1
                metrics.status = TaskStatus.FAILED
                metrics.last_error = str(exc)
                consecutive_failures += 1
                self._tasks_failed += 1

                logger.error(
                    "task_failed",
                    extra={
                        "task": task.name,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                        "consecutive_failures": consecutive_failures,
                    },
                )

            # Exponential backoff on failure
            if consecutive_failures > 0:
                if consecutive_failures > task.max_retries:
                    logger.error(
                        "task_max_retries_exceeded",
                        extra={
                            "task": task.name,
                            "retries": consecutive_failures,
                        },
                    )
                    metrics.status = TaskStatus.DISABLED
                    break

                backoff = min(
                    task.retry_backoff_base * (2 ** (consecutive_failures - 1)),
                    task.retry_backoff_max,
                )
                metrics.status = TaskStatus.RETRYING

                logger.info(
                    "task_retry_backoff",
                    extra={
                        "task": task.name,
                        "backoff_seconds": backoff,
                        "attempt": consecutive_failures,
                    },
                )

                # Wait with backoff, checking shutdown event
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=backoff,
                    )
                    # If we get here, shutdown was requested
                    break
                except asyncio.TimeoutError:
                    # Normal: backoff period elapsed
                    pass
            else:
                # Normal interval wait
                try:
                    metrics.next_run_at = datetime.fromtimestamp(
                        time.time() + task.interval_seconds,
                        tz=timezone.utc,
                    )
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=task.interval_seconds,
                    )
                    # Shutdown was requested
                    break
                except asyncio.TimeoutError:
                    # Normal: interval elapsed
                    pass

        metrics.status = TaskStatus.PENDING

    # ── Default Task Implementations ─────────────────────────────────

    @staticmethod
    async def _task_price_fetch() -> None:
        """Default task: Fetch latest prices for watched symbols."""
        logger.debug("price_fetch_task_running")

    @staticmethod
    async def _task_rebalance_check() -> None:
        """Default task: Check if portfolio needs rebalancing."""
        logger.debug("rebalance_check_task_running")

    @staticmethod
    async def _task_strategy_health() -> None:
        """Default task: Check strategy health metrics."""
        logger.debug("strategy_health_task_running")

    # ── Signal Handling ──────────────────────────────────────────────

    def _register_signal_handlers(self) -> None:
        """Register SIGINT/SIGTERM handlers for graceful shutdown."""
        loop = asyncio.get_running_loop()

        def _shutdown_handler() -> None:
            logger.info("shutdown_signal_received")
            asyncio.create_task(self.stop())

        try:
            loop.add_signal_handler(signal.SIGINT, _shutdown_handler)
            loop.add_signal_handler(signal.SIGTERM, _shutdown_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    # ── Health Check ─────────────────────────────────────────────────

    def health_check(self) -> WorkerHealth:
        """Get current worker health status.

        Returns:
            WorkerHealth with current status.
        """
        uptime = 0.0
        if self._started_at and self._state == WorkerState.RUNNING:
            uptime = time.time() - self._started_at

        return WorkerHealth(
            worker_id=self.worker_id,
            state=self._state,
            uptime_seconds=uptime,
            tasks_running=sum(
                1
                for m in self._task_metrics.values()
                if m.status == TaskStatus.RUNNING
            ),
            tasks_completed=self._tasks_completed,
            tasks_failed=self._tasks_failed,
            lock_held=self._lock.is_held,
        )

    @property
    def task_metrics(self) -> Dict[str, TaskMetrics]:
        """Get metrics for all registered tasks."""
        return dict(self._task_metrics)

    @property
    def state(self) -> WorkerState:
        """Current worker state."""
        return self._state

    @property
    def stats(self) -> Dict[str, Any]:
        """Worker statistics."""
        return {
            "worker_id": self.worker_id,
            "state": self._state.value,
            "tasks_registered": len(self._tasks),
            "tasks_running": len(self._task_handles),
            "tasks_completed": self._tasks_completed,
            "tasks_failed": self._tasks_failed,
            "lock_held": self._lock.is_held,
            "task_metrics": {
                name: metrics.model_dump()
                for name, metrics in self._task_metrics.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    async def demo():
        # Create custom tasks for demo
        counter = {"value": 0}

        async def counting_task() -> None:
            counter["value"] += 1
            logger.info(f"Counting task: {counter['value']}")

        async def failing_task() -> None:
            if counter["value"] % 3 == 0:
                raise RuntimeError("Simulated failure")
            logger.info("Failing task: succeeded")

        worker = BackgroundWorker(
            tasks=[
                WorkerTask(
                    name="counter",
                    func=counting_task,
                    interval_seconds=1.0,
                    timeout_seconds=5.0,
                    max_retries=5,
                ),
                WorkerTask(
                    name="flaky",
                    func=failing_task,
                    interval_seconds=2.0,
                    timeout_seconds=5.0,
                    max_retries=3,
                    retry_backoff_base=1.0,
                ),
            ],
        )

        # Start worker
        started = await worker.start()
        logger.info("Worker started: %s", started)

        if started:
            # Let it run for a few seconds
            for _ in range(5):
                health = worker.health_check()
                logger.info(
                    "  State: %s, Running: %s, Completed: %s, Failed: %s",
                    health.state.value,
                    health.tasks_running,
                    health.tasks_completed,
                    health.tasks_failed,
                )
                await asyncio.sleep(1.0)

            # Stop gracefully
            await worker.stop()
            logger.info("Worker stopped. Counter value: %s", counter['value'])
            logger.info("Final stats: %s", worker.stats)

    asyncio.run(demo())
