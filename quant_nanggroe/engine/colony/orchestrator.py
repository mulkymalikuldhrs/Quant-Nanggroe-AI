"""Colony orchestrator — manages a pool of workers and dispatches tasks.

Uses asyncio.gather() for parallel execution. Workers run independently;
one failure is isolated and reported without crashing the colony.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.colony.message_bus import MessageBus
from quant_nanggroe.engine.colony.tasks import Task, TaskStatus, TaskType
from quant_nanggroe.engine.colony.worker import (
    DataWorker,
    ExecutionWorker,
    RiskWorker,
    StrategyWorker,
    Worker,
)


@dataclass
class ColonyOrchestrator:
    """Manages a colony of workers and dispatches batches of tasks.

    Usage:
        colony = ColonyOrchestrator()
        colony.add_worker(StrategyWorker(role="ma_cross", goal="Generate MA crossover signals"))
        results = await colony.run_batch([task1, task2, task3])
        print(colony.status())
    """

    bus: MessageBus = field(default_factory=MessageBus)
    workers: List[Worker] = field(default_factory=list)
    _history: List[Task] = field(default_factory=list)

    def add_worker(self, worker: Worker) -> None:
        worker.bus = self.bus
        self.workers.append(worker)

    # ── Factory helpers ───────────────────────────────────────────────

    def add_strategy_worker(self, role: str, goal: str, toolset: Optional[List[str]] = None) -> StrategyWorker:
        w = StrategyWorker(role=role, goal=goal, toolset=toolset or [], bus=self.bus)
        self.workers.append(w)
        return w

    def add_risk_worker(self, role: str, goal: str) -> RiskWorker:
        w = RiskWorker(role=role, goal=goal, bus=self.bus)
        self.workers.append(w)
        return w

    def add_data_worker(self, role: str, goal: str) -> DataWorker:
        w = DataWorker(role=role, goal=goal, bus=self.bus)
        self.workers.append(w)
        return w

    def add_execution_worker(self, role: str, goal: str) -> ExecutionWorker:
        w = ExecutionWorker(role=role, goal=goal, bus=self.bus)
        self.workers.append(w)
        return w

    # ── Dispatch ──────────────────────────────────────────────────────

    def _pick_worker(self, task: Task) -> Worker:
        """Pick the first worker whose role-type matches the task type."""
        type_map = {
            TaskType.STRATEGY: StrategyWorker,
            TaskType.RISK: RiskWorker,
            TaskType.DATA: DataWorker,
            TaskType.EXECUTION: ExecutionWorker,
        }
        cls = type_map.get(task.type)
        if cls is None:
            raise ValueError(f"No worker type for task type {task.type}")
        for w in self.workers:
            if isinstance(w, cls):
                return w
        raise RuntimeError(f"No {cls.__name__} registered in colony")

    async def run(self, task: Task) -> Task:
        """Dispatch a single task to the appropriate worker."""
        worker = self._pick_worker(task)
        result = await worker.run(task)
        self._history.append(result)
        return result

    async def run_batch(self, tasks: List[Task]) -> List[Task]:
        """Dispatch a batch of tasks in parallel via asyncio.gather().

        One task failure does not cancel others — each worker runs in an
        isolated coroutine.
        """
        if not self.workers:
            raise RuntimeError("No workers registered in colony")

        coros = [self.run(t) for t in tasks]

        # asyncio.gather(return_exceptions=True) so one failure doesn't kill the batch
        results: List[Any] = await asyncio.gather(*coros, return_exceptions=True)

        final: List[Task] = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                tasks[i].status = TaskStatus.FAILED
                tasks[i].error = str(res)
                final.append(tasks[i])
            else:
                final.append(res)
        return final

    # ── Status ────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Snapshot of colony state."""
        return {
            "workers": [
                {"role": w.role, "goal": w.goal, "type": type(w).__name__}
                for w in self.workers
            ],
            "total_tasks_dispatched": len(self._history),
            "last_tasks": [
                {"id": t.id, "type": t.type.value, "name": t.name, "status": t.status.value}
                for t in self._history[-10:]
            ],
        }

    def workers_busy(self) -> List[str]:
        """Return roles of workers currently running (no direct tracking yet)."""
        # ponytail: in-memory tracking, add per-worker state if throughput matters
        return []

    def clear_history(self) -> None:
        self._history.clear()
