"""Task type definitions for the colony execution framework.

Strategy, risk, data, and execution tasks with Pydantic models
compatible with FastAPI-style serialisation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    STRATEGY = "strategy"
    RISK = "risk"
    DATA = "data"
    EXECUTION = "execution"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Task(BaseModel):
    """A unit of work dispatched to a worker."""
    id: str = Field(default_factory=lambda: f"task_{datetime.utcnow().timestamp()}")
    type: TaskType
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ── Convenience constructors ──────────────────────────────────────────

def strategy_task(name: str, strategy_params: Optional[Dict[str, Any]] = None) -> Task:
    return Task(type=TaskType.STRATEGY, name=name, params=strategy_params or {})


def risk_task(name: str, risk_params: Optional[Dict[str, Any]] = None) -> Task:
    return Task(type=TaskType.RISK, name=name, params=risk_params or {})


def data_task(name: str, data_params: Optional[Dict[str, Any]] = None) -> Task:
    return Task(type=TaskType.DATA, name=name, params=data_params or {})


def execution_task(name: str, exec_params: Optional[Dict[str, Any]] = None) -> Task:
    return Task(type=TaskType.EXECUTION, name=name, params=exec_params or {})
