"""Planning agent – MetaGPT SOP-driven task decomposition.

Implements Standard Operating Procedure (SOP) driven planning: match a task
to an SOP template, break it down into pipeline stages, construct a
dependency graph, and estimate timelines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..types import AgentSpec, AgentType, Task
from .base import BaseAgent

logger = logging.getLogger(__name__)

# ── SOP Templates ───────────────────────────────────────────────────────────

SOP_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "software_development": {
        "name": "Software Development",
        "stages": [
            {"stage": "requirements", "agent_type": "researcher", "description": "Gather requirements"},
            {"stage": "design", "agent_type": "planner", "description": "Design architecture"},
            {"stage": "coding", "agent_type": "coder", "description": "Implement solution"},
            {"stage": "testing", "agent_type": "coder", "description": "Write and run tests"},
            {"stage": "review", "agent_type": "security", "description": "Security and code review"},
            {"stage": "deploy", "agent_type": "executor", "description": "Deploy to environment"},
        ],
    },
    "research_analysis": {
        "name": "Research & Analysis",
        "stages": [
            {"stage": "search", "agent_type": "researcher", "description": "Search for information"},
            {"stage": "analyze", "agent_type": "researcher", "description": "Analyze findings"},
            {"stage": "summarize", "agent_type": "planner", "description": "Synthesize report"},
        ],
    },
    "security_audit": {
        "name": "Security Audit",
        "stages": [
            {"stage": "scan", "agent_type": "security", "description": "Vulnerability scan"},
            {"stage": "dependency_audit", "agent_type": "security", "description": "Dependency audit"},
            {"stage": "secret_scan", "agent_type": "security", "description": "Secret detection"},
            {"stage": "report", "agent_type": "researcher", "description": "Generate audit report"},
        ],
    },
    "data_pipeline": {
        "name": "Data Pipeline",
        "stages": [
            {"stage": "extract", "agent_type": "browser", "description": "Extract data"},
            {"stage": "transform", "agent_type": "executor", "description": "Transform data"},
            {"stage": "load", "agent_type": "executor", "description": "Load into target"},
            {"stage": "validate", "agent_type": "coder", "description": "Validate pipeline"},
        ],
    },
    "general": {
        "name": "General Purpose",
        "stages": [
            {"stage": "research", "agent_type": "researcher", "description": "Research context"},
            {"stage": "plan", "agent_type": "planner", "description": "Plan approach"},
            {"stage": "execute", "agent_type": "executor", "description": "Execute plan"},
            {"stage": "validate", "agent_type": "coder", "description": "Validate results"},
        ],
    },
}


class PlannerAgent(BaseAgent):
    """MetaGPT SOP-driven planning agent.

    Workflow
    --------
    1. :meth:`_match_sop` – match the task to an SOP template.
    2. :meth:`_build_pipeline` – convert the template into a pipeline of
       subtasks with stage metadata.
    3. :meth:`_build_dependency_graph` – compute inter-stage dependencies.
    4. :meth:`_estimate_timeline` – produce time and effort estimates.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.PLANNER, autonomy_level=2)
        if spec.agent_type != AgentType.PLANNER:
            spec.agent_type = AgentType.PLANNER
        super().__init__(spec=spec, **kwargs)
        self._plans: Dict[str, List[Dict]] = {}
        self._dependency_graphs: Dict[str, Dict[str, List[str]]] = {}
        self._timelines: Dict[str, Dict[str, Any]] = {}

    # ── Abstract hook implementations ──

    async def on_task(self, task: Task) -> Any:
        """Decompose task using SOP matching and dependency analysis."""
        plan = await self.decompose(task)
        self._plans[task.task_id] = plan

        # Build dependency graph
        dep_graph = self._build_dependency_graph(plan)
        self._dependency_graphs[task.task_id] = dep_graph

        # Estimate timeline
        timeline = self._estimate_timeline(plan)
        self._timelines[task.task_id] = timeline

        return {
            "plan_id": task.task_id,
            "subtasks": plan,
            "total_steps": len(plan),
            "dependency_graph": dep_graph,
            "timeline": timeline,
        }

    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle A2A messages for plan queries and updates."""
        msg_type = message.get("message_type", "")
        if msg_type == "plan_query":
            task_id = message.get("payload", {}).get("task_id", "")
            return {
                "plan": self._plans.get(task_id),
                "dependencies": self._dependency_graphs.get(task_id),
                "timeline": self._timelines.get(task_id),
            }
        elif msg_type == "plan_update":
            task_id = message.get("payload", {}).get("task_id", "")
            updates = message.get("payload", {}).get("updates", {})
            return self._apply_plan_update(task_id, updates)
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        """Declare planner capabilities."""
        return [
            "task_decomposition", "sop_matching", "pipeline_generation",
            "dependency_graph", "timeline_estimation", "effort_estimation",
        ]

    # ── SOP matching ──

    def _match_sop(self, task: Task) -> str:
        """Match a task to an SOP template name.

        Uses keyword heuristics on the task description and payload.
        """
        description = task.description.lower()
        payload = task.payload

        # Check explicit SOP hint
        if "sop" in payload:
            sop_name = payload["sop"]
            if sop_name in SOP_TEMPLATES:
                return sop_name

        # Keyword heuristics
        dev_keywords = ["develop", "build", "implement", "create", "code", "feature", "api"]
        research_keywords = ["research", "analyze", "investigate", "study", "survey"]
        security_keywords = ["security", "audit", "vulnerability", "scan", "compliance"]
        data_keywords = ["pipeline", "etl", "data", "extract", "transform", "load"]

        if any(kw in description for kw in dev_keywords):
            return "software_development"
        if any(kw in description for kw in research_keywords):
            return "research_analysis"
        if any(kw in description for kw in security_keywords):
            return "security_audit"
        if any(kw in description for kw in data_keywords):
            return "data_pipeline"

        return "general"

    # ── Decomposition ──

    async def decompose(self, task: Task) -> List[Dict]:
        """Decompose a task into ordered subtasks using SOP matching."""
        sop_name = self._match_sop(task)
        template = SOP_TEMPLATES.get(sop_name, SOP_TEMPLATES["general"])

        subtasks: List[Dict[str, Any]] = []
        for i, stage in enumerate(template["stages"]):
            dependencies = [f"{task.task_id}-{j}" for j in range(i)] if i > 0 else []
            subtasks.append({
                "subtask_id": f"{task.task_id}-{i}",
                "stage": stage["stage"],
                "description": f"{stage['description']}: {task.description}",
                "agent_type": stage["agent_type"],
                "dependencies": dependencies,
                "sop_template": sop_name,
                "order": i,
            })
        return subtasks

    # ── Dependency graph ──

    def _build_dependency_graph(self, plan: List[Dict]) -> Dict[str, List[str]]:
        """Construct a dependency graph from plan subtasks.

        Returns a mapping of ``subtask_id → [dependency_subtask_ids]``.
        """
        graph: Dict[str, List[str]] = {}
        for subtask in plan:
            subtask_id = subtask["subtask_id"]
            deps = subtask.get("dependencies", [])
            graph[subtask_id] = deps
        return graph

    def _apply_plan_update(self, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Apply in-place updates to a stored plan."""
        plan = self._plans.get(task_id, [])
        for update in updates.get("changes", []):
            subtask_id = update.get("subtask_id")
            for subtask in plan:
                if subtask["subtask_id"] == subtask_id:
                    subtask.update(update.get("data", {}))
        return {"updated": True, "task_id": task_id}

    # ── Timeline estimation ──

    def _estimate_timeline(self, plan: List[Dict]) -> Dict[str, Any]:
        """Estimate execution timeline for a plan.

        Each stage is estimated at 30 seconds base with a complexity
        multiplier derived from the number of dependencies.
        """
        stage_durations: Dict[str, float] = {}
        for subtask in plan:
            dep_count = len(subtask.get("dependencies", []))
            # Base 30s + 10s per dependency (fan-in cost)
            duration = 30_000 + dep_count * 10_000
            stage_durations[subtask["subtask_id"]] = duration

        # Critical path = total sequential duration (simplified)
        total_ms = sum(stage_durations.values())
        parallel_groups = self._count_parallel_groups(plan)

        estimated_wall_ms = total_ms / max(1, parallel_groups) if parallel_groups > 1 else total_ms

        return {
            "total_subtasks": len(plan),
            "estimated_total_ms": total_ms,
            "estimated_wall_ms": int(estimated_wall_ms),
            "parallel_groups": parallel_groups,
            "critical_path_length": len(plan),
            "stage_durations_ms": stage_durations,
        }

    # ── Accessors ──

    def get_plan(self, task_id: str) -> Optional[List[Dict]]:
        """Retrieve a stored plan by task ID."""
        return self._plans.get(task_id)

    def get_dependency_graph(self, task_id: str) -> Optional[Dict[str, List[str]]]:
        """Retrieve the dependency graph for a task."""
        return self._dependency_graphs.get(task_id)

    def get_timeline(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the timeline estimate for a task."""
        return self._timelines.get(task_id)

    def estimate_effort(self, plan: List[Dict]) -> Dict[str, Any]:
        """Estimate effort for a plan (public convenience method)."""
        return self._estimate_timeline(plan)

    def _count_parallel_groups(self, plan: List[Dict]) -> int:
        """Count groups of subtasks that can run in parallel."""
        if not plan:
            return 0
        deps = [len(s.get("dependencies", [])) for s in plan]
        return max(1, len([d for d in deps if d == 0]))
