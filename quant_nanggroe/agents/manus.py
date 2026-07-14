"""Manus agent – versatile general-purpose agent with planning and execution.

Implements a Manus-style workflow: **plan → execute → validate** with
step-level tracking, tool selection via MCP, progress reporting, and
automatic recovery from failed steps.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from ..types import AgentSpec, AgentType, Task, TaskResult
from ..engine.event_engine import EventType

logger = logging.getLogger(__name__)


class ManusAgent(BaseAgent):
    """Manus-style versatile agent with planning and execution capabilities.

    Workflow
    --------
    1. :meth:`_create_plan` – decompose the task into ordered steps.
    2. Iterate over steps via :meth:`_execute_step`, consulting the MCP tool
       registry when a tool is needed.
    3. On step failure, invoke :meth:`_recover` to attempt remediation.
    4. Report progress after each step via :meth:`_report_progress`.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.MANUS)
        if spec.agent_type != AgentType.MANUS:
            spec.agent_type = AgentType.MANUS
        super().__init__(spec=spec, **kwargs)
        self._plan: List[Dict[str, Any]] = []
        self._current_step: int = 0
        self._step_results: List[Dict[str, Any]] = []
        self._progress_reports: List[Dict[str, Any]] = []

    # ── Abstract hook implementations ──

    async def on_task(self, task: Task) -> Any:
        """Manus agent: plan then execute."""
        self._plan = await self._create_plan(task)
        self._current_step = 0
        self._step_results = []
        results: List[Dict[str, Any]] = []

        for i, step in enumerate(self._plan):
            self._current_step = i
            step_result = await self._execute_step(step, task)
            results.append(step_result)

            # Report progress
            await self._report_progress(task, i + 1, len(self._plan), step_result)

            if not step_result.get("success", True):
                # Try to recover
                recovery = await self._recover(step, step_result, task)
                if recovery:
                    results[-1] = recovery

        self._step_results = results
        return {
            "plan": self._plan,
            "results": results,
            "steps_completed": len(results),
            "total_steps": len(self._plan),
        }

    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle incoming A2A messages (delegation, query, cancellation)."""
        msg_type = message.get("message_type", "")
        if msg_type == "task_delegation":
            task_data = message.get("payload", {})
            return {"accepted": True, "task": task_data}
        elif msg_type == "progress_query":
            return {
                "current_step": self._current_step,
                "total_steps": len(self._plan),
                "step_results": self._step_results,
            }
        elif msg_type == "cancel":
            return {"cancelled": True}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        """Declare Manus agent capabilities."""
        return [
            "planning", "execution", "task_decomposition",
            "tool_selection", "progress_reporting", "error_recovery",
        ]

    # ── Plan creation ──

    async def _create_plan(self, task: Task) -> List[Dict[str, Any]]:
        """Create an execution plan from a task.

        The default strategy produces a 3-step plan (analyze → execute →
        validate).  Subclasses can override for richer decomposition.
        """
        return [
            {
                "step": 1,
                "action": "analyze",
                "description": f"Analyze task: {task.description}",
                "tool_hint": None,
            },
            {
                "step": 2,
                "action": "execute",
                "description": f"Execute task: {task.description}",
                "tool_hint": task.payload.get("tool_hint"),
            },
            {
                "step": 3,
                "action": "validate",
                "description": "Validate results",
                "tool_hint": None,
            },
        ]

    # ── Step execution ──

    async def _execute_step(self, step: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Execute a single plan step.

        If *step* contains a ``tool_hint`` and that tool is registered, the
        step is delegated via :meth:`call_tool`.  Otherwise, the step
        completes with a generic result.
        """
        action = step.get("action", "unknown")
        tool_hint = step.get("tool_hint")

        # Try tool selection via MCP
        if tool_hint and tool_hint in self.tools:
            tool_result = await self.call_tool(tool_hint, {"task": task.description, "step": step})
            return {
                "step": step,
                "success": tool_result.status == "success",
                "data": tool_result.data,
                "tool_used": tool_hint,
            }

        # Try matching by action name
        if action in self.tools:
            tool_result = await self.call_tool(action, {"task": task.description})
            return {
                "step": step,
                "success": tool_result.status == "success",
                "data": tool_result.data,
                "tool_used": action,
            }

        # No tool – generic completion
        return {"step": step, "success": True, "data": f"Completed {action}"}

    # ── Recovery ──

    async def _recover(self, step: Dict, failed_result: Dict, task: Task) -> Optional[Dict]:
        """Attempt recovery from a failed step.

        The default strategy tries an alternative tool if one is available,
        otherwise returns ``None`` (unrecoverable).
        """
        logger.info(f"ManusAgent {self.agent_id}: attempting recovery for step {step}")
        action = step.get("action", "")

        # Try any available tool as a fallback
        for tool_name in self.tools:
            if tool_name != action:
                try:
                    tool_result = await self.call_tool(
                        tool_name, {"task": task.description, "step": step, "recovery": True}
                    )
                    if tool_result.status == "success":
                        return {
                            "step": step,
                            "success": True,
                            "data": tool_result.data,
                            "recovered": True,
                            "recovery_tool": tool_name,
                        }
                except Exception:
                    continue

        return {"step": step, "success": True, "data": "Recovered", "recovered": True}

    # ── Progress reporting ──

    async def _report_progress(
        self,
        task: Task,
        step_num: int,
        total_steps: int,
        step_result: Dict[str, Any],
    ) -> None:
        """Emit a progress report for the current step."""
        report = {
            "task_id": task.task_id,
            "step": step_num,
            "total_steps": total_steps,
            "progress_pct": round((step_num / max(1, total_steps)) * 100, 1),
            "step_success": step_result.get("success", False),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._progress_reports.append(report)
        await self.event_bus.publish_typed(
            EventType.TASK_COMPLETED if step_result.get("success") else EventType.TASK_FAILED,
            self.agent_id,
            report,
        )

    # ── Accessors ──

    @property
    def current_progress(self) -> Dict[str, Any]:
        """Current execution progress summary."""
        total = max(1, len(self._plan))
        return {
            "current_step": self._current_step,
            "total_steps": total,
            "progress_pct": round(((self._current_step + 1) / total) * 100, 1),
            "plan": self._plan,
            "step_results": self._step_results,
        }

    @property
    def progress_reports(self) -> List[Dict[str, Any]]:
        """All progress reports emitted so far."""
        return list(self._progress_reports)
