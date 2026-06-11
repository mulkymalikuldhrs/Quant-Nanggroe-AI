"""Task API routes.

Endpoints:
* POST /api/v1/tasks           – create task
* GET  /api/v1/tasks           – list tasks
* GET  /api/v1/tasks/{id}      – task status
* GET  /api/v1/tasks/{id}/result – task result
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..schemas import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskStatusResponse,
    TaskResultResponse,
)

logger = logging.getLogger(__name__)


class TaskRoutes:
    """Route handlers for task operations."""

    def __init__(self, colony_manager: Any = None, task_scheduler: Any = None):
        self._colony_manager = colony_manager
        self._task_scheduler = task_scheduler

    async def create_task(self, request: Optional[TaskCreateRequest] = None, **kwargs: Any) -> Dict[str, Any]:
        """POST /api/v1/tasks – create a new task."""
        if request is None:
            data = kwargs.get("body", kwargs)
            request = TaskCreateRequest(
                description=data.get("description", ""),
                colony_id=data.get("colony_id"),
                priority=data.get("priority", 2),
                payload=data.get("payload", {}),
                required_capabilities=data.get("required_capabilities", []),
                timeout_ms=data.get("timeout_ms", 300_000),
            )

        from ...types import Task, TaskPriority

        try:
            priority = TaskPriority(request.priority)
        except ValueError:
            priority = TaskPriority.MEDIUM

        task = Task(
            description=request.description,
            colony_id=request.colony_id,
            priority=priority,
            payload=request.payload,
            required_capabilities=request.required_capabilities,
            timeout_ms=request.timeout_ms,
        )

        # Submit to scheduler if available
        if self._task_scheduler and hasattr(self._task_scheduler, "submit"):
            self._task_scheduler.submit(task)
        # Or submit to colony if specified
        elif self._colony_manager and request.colony_id:
            colony = self._colony_manager.get_colony(request.colony_id)
            if colony:
                await colony.submit_task(task)

        return TaskCreateResponse(
            task_id=task.task_id,
            colony_id=request.colony_id,
        ).model_dump(mode="json")

    async def list_tasks(self, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/tasks – list tasks."""
        tasks = []

        if self._task_scheduler and hasattr(self._task_scheduler, "get_stats"):
            stats = self._task_scheduler.get_stats()
            tasks.append({
                "scheduler_stats": stats,
            })

        return {"tasks": tasks, "total": len(tasks)}

    async def get_task(self, task_id: str, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/tasks/{id} – get task status."""
        if self._task_scheduler and hasattr(self._task_scheduler, "get_task"):
            task = self._task_scheduler.get_task(task_id)
            if task:
                return TaskStatusResponse(
                    task_id=task.task_id,
                    description=task.description,
                    status=task.status.value,
                    priority=task.priority.value,
                    assigned_agent=task.assigned_agent,
                    colony_id=task.colony_id,
                    created_at=task.created_at.isoformat() if task.created_at else None,
                    completed_at=task.completed_at.isoformat() if task.completed_at else None,
                    error=task.error,
                ).model_dump(mode="json")

        return {"error": f"Task {task_id} not found", "code": "TASK_NOT_FOUND"}

    async def get_task_result(self, task_id: str, **kwargs: Any) -> Dict[str, Any]:
        """GET /api/v1/tasks/{id}/result – get task result."""
        if self._task_scheduler and hasattr(self._task_scheduler, "get_result"):
            result = self._task_scheduler.get_result(task_id)
            if result:
                return TaskResultResponse(
                    task_id=result.task_id,
                    success=result.success,
                    data=result.data,
                    error=result.error,
                    execution_time_ms=result.execution_time_ms,
                    tools_used=result.tools_used,
                ).model_dump(mode="json")

        return {"error": f"Result for task {task_id} not found", "code": "TASK_RESULT_NOT_FOUND"}
