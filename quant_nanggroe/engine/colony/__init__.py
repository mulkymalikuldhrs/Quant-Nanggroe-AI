"""Colony — parallel execution framework for Quant-Nanggroe-AI.

Manages a pool of worker agents (strategy, risk, data, execution)
that execute tasks in parallel via asyncio.gather() with error isolation.
"""

from quant_nanggroe.engine.colony.message_bus import Message, MessageBus
from quant_nanggroe.engine.colony.orchestrator import ColonyOrchestrator
from quant_nanggroe.engine.colony.tasks import (
    Task,
    TaskStatus,
    TaskType,
    data_task,
    execution_task,
    risk_task,
    strategy_task,
)
from quant_nanggroe.engine.colony.worker import (
    DataWorker,
    ExecutionWorker,
    RiskWorker,
    StrategyWorker,
    Worker,
)

__all__ = [
    "ColonyOrchestrator",
    "Message",
    "MessageBus",
    "Task",
    "TaskStatus",
    "TaskType",
    "Worker",
    "StrategyWorker",
    "RiskWorker",
    "DataWorker",
    "ExecutionWorker",
    "strategy_task",
    "risk_task",
    "data_task",
    "execution_task",
]
