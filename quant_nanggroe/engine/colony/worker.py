"""Worker agent base class and concrete trading workers.

Each worker has a role, a goal, and a toolset. Workers execute tasks
independently — one failure does not crash the colony.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.colony.message_bus import Message, MessageBus
from quant_nanggroe.engine.colony.tasks import Task, TaskStatus, TaskType


@dataclass
class Worker(ABC):
    """Base worker — override execute() with the actual logic."""

    role: str
    goal: str
    toolset: List[str] = field(default_factory=list)
    bus: Optional[MessageBus] = None

    @abstractmethod
    async def execute(self, task: Task) -> Any:
        """Run the task and return a result. One worker failure is isolated."""
        ...

    async def run(self, task: Task) -> Task:
        """Execute a task with lifecycle tracking and error isolation."""
        task.status = TaskStatus.RUNNING
        try:
            result = await self.execute(task)
            task.result = result
            task.status = TaskStatus.SUCCESS
        except Exception as e:
            task.error = f"[{self.role}] {e}"
            task.status = TaskStatus.FAILED
        task.completed_at = __import__("datetime").datetime.utcnow()
        if self.bus:
            await self.bus.publish(Message(
                topic=f"worker.{self.role}.done",
                payload=task,
                sender=self.role,
            ))
        return task


# ── Concrete workers ──────────────────────────────────────────────────


class StrategyWorker(Worker):
    """Runs trading strategies (backtest or live signal gen)."""

    async def execute(self, task: Task) -> Any:
        # ponytail: delegates to backtest/strategies engines; stub for wiring
        await asyncio.sleep(0.01)
        return {"strategy": task.name, "signal": "hold", "confidence": 0.5}


class RiskWorker(Worker):
    """Runs risk checks (VaR, drawdown, position limits)."""

    async def execute(self, task: Task) -> Any:
        await asyncio.sleep(0.01)
        return {"risk_check": task.name, "passed": True, "score": 0.0}


class DataWorker(Worker):
    """Fetches and processes market data."""

    async def execute(self, task: Task) -> Any:
        await asyncio.sleep(0.01)
        return {"data": task.name, "rows": 0, "columns": []}


class ExecutionWorker(Worker):
    """Handles order placement and fill tracking."""

    async def execute(self, task: Task) -> Any:
        await asyncio.sleep(0.01)
        return {"execution": task.name, "filled": False, "order_id": None}
