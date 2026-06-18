"""LangGraph-based agent execution graph.

Implements a structured execution graph with nodes for planning,
execution, and review.  Supports conditional routing, parallel
branch execution, checkpointing, and error recovery – patterns
inspired by DeerFlow's LangGraph orchestration.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class HarnessNodeStatus(str, Enum):
    """Status of a harness graph node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class HarnessGraphStatus(str, Enum):
    """Status of the entire harness graph."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class NodeRole(str, Enum):
    """Role classification for harness nodes."""
    PLANNER = "planner"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    TOOL = "tool"
    CONDITION = "condition"
    FORK = "fork"
    MERGE = "merge"


# ── Data Models ──────────────────────────────────────────────────────────────


class HarnessCheckpoint(BaseModel):
    """Serializable checkpoint of harness execution state."""
    model_config = ConfigDict(frozen=False)

    checkpoint_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    graph_id: str = ""
    node_statuses: Dict[str, HarnessNodeStatus] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)
    current_node: Optional[str] = None
    step_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionStep(BaseModel):
    """Record of a single execution step."""
    model_config = ConfigDict(frozen=False)

    step_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    node_name: str = ""
    role: NodeRole = NodeRole.EXECUTOR
    status: HarnessNodeStatus = HarnessNodeStatus.PENDING
    input_state: Dict[str, Any] = Field(default_factory=dict)
    output_state: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Node ─────────────────────────────────────────────────────────────────────


class HarnessNode:
    """A node in the harness execution graph.

    Each node has a role (planner, executor, reviewer, etc.), an async
    action, and optional conditional edges for dynamic routing.
    """

    def __init__(
        self,
        name: str,
        role: NodeRole = NodeRole.EXECUTOR,
        action: Optional[Callable[..., Any]] = None,
        max_retries: int = 3,
        timeout_s: float = 300.0,
    ):
        self.name = name
        self.role = role
        self.action = action
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.status: HarnessNodeStatus = HarnessNodeStatus.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self._retry_count: int = 0
        self._edges: List[str] = []
        self._conditional_edge: Optional[Callable[[Dict[str, Any]], str]] = None
        self._conditional_targets: Dict[str, str] = {}

    def add_edge(self, target: str) -> None:
        """Add an unconditional edge to target node."""
        self._edges.append(target)

    def add_conditional_edge(
        self,
        condition: Callable[[Dict[str, Any]], str],
        targets: Optional[Dict[str, str]] = None,
    ) -> None:
        """Add a conditional edge."""
        self._conditional_edge = condition
        self._conditional_targets = targets or {}

    def get_next_node(self, state: Dict[str, Any]) -> Optional[str]:
        """Determine the next node based on state."""
        if self._conditional_edge is not None:
            try:
                result = self._conditional_edge(state)
                if result in self._conditional_targets:
                    return self._conditional_targets[result]
                return result
            except Exception as e:
                logger.warning("Conditional edge error in %s: %s", self.name, e)

        if self._edges:
            return self._edges[0]
        return None


# ── Harness Graph ────────────────────────────────────────────────────────────


class HarnessGraph:
    """LangGraph-style execution graph for agent orchestration.

    Implements a Planning → Execution → Review workflow with:
    * Conditional routing between phases
    * Parallel execution support
    * Checkpointing and resume
    * Error recovery with retry and fallback
    * Step-by-step execution logging

    Usage::

        graph = HarnessGraph("research_workflow")
        graph.add_planner("plan", plan_action)
        graph.add_executor("execute", execute_action)
        graph.add_reviewer("review", review_action)
        graph.add_edge("plan", "execute")
        graph.add_edge("execute", "review")

        result = await graph.run({"query": "analyze market trends"})
    """

    def __init__(self, graph_id: str = "", max_steps: int = 200):
        self.graph_id = graph_id or f"harness-{uuid.uuid4().hex[:8]}"
        self._nodes: Dict[str, HarnessNode] = {}
        self._entry_node: Optional[str] = None
        self._exit_nodes: Set[str] = set()
        self._error_paths: Dict[str, str] = {}
        self._status: HarnessGraphStatus = HarnessGraphStatus.PENDING
        self._execution_log: List[ExecutionStep] = []
        self._checkpoints: List[HarnessCheckpoint] = []
        self._max_steps = max_steps
        self._parallel_groups: Dict[str, List[str]] = {}

    # ── Graph construction ──────────────────────────────────────────────

    def add_planner(
        self, name: str, action: Optional[Callable] = None, **kwargs: Any,
    ) -> HarnessNode:
        """Add a planner node."""
        node = HarnessNode(name=name, role=NodeRole.PLANNER, action=action, **kwargs)
        self._nodes[name] = node
        if self._entry_node is None:
            self._entry_node = name
        return node

    def add_executor(
        self, name: str, action: Optional[Callable] = None, **kwargs: Any,
    ) -> HarnessNode:
        """Add an executor node."""
        node = HarnessNode(name=name, role=NodeRole.EXECUTOR, action=action, **kwargs)
        self._nodes[name] = node
        return node

    def add_reviewer(
        self, name: str, action: Optional[Callable] = None, **kwargs: Any,
    ) -> HarnessNode:
        """Add a reviewer node and mark as exit."""
        node = HarnessNode(name=name, role=NodeRole.REVIEWER, action=action, **kwargs)
        self._nodes[name] = node
        self._exit_nodes.add(name)
        return node

    def add_tool_node(
        self, name: str, action: Optional[Callable] = None, **kwargs: Any,
    ) -> HarnessNode:
        """Add a tool node."""
        node = HarnessNode(name=name, role=NodeRole.TOOL, action=action, **kwargs)
        self._nodes[name] = node
        return node

    def add_node(
        self,
        name: str,
        action: Optional[Callable] = None,
        role: NodeRole = NodeRole.EXECUTOR,
        **kwargs: Any,
    ) -> HarnessNode:
        """Add a generic node."""
        node = HarnessNode(name=name, role=role, action=action, **kwargs)
        self._nodes[name] = node
        return node

    def add_edge(self, source: str, target: str) -> None:
        """Add an unconditional edge."""
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        if target not in self._nodes and target not in self._parallel_groups:
            raise ValueError(f"Target '{target}' not found")
        self._nodes[source].add_edge(target)

    def add_conditional_edge(
        self,
        source: str,
        condition: Callable[[Dict[str, Any]], str],
        targets: Optional[Dict[str, str]] = None,
    ) -> None:
        """Add a conditional edge."""
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        self._nodes[source].add_conditional_edge(condition, targets)

    def add_error_path(self, node_name: str, fallback_node: str) -> None:
        """Define a fallback node on failure."""
        self._error_paths[node_name] = fallback_node

    def add_parallel_group(self, name: str, node_names: List[str]) -> None:
        """Register a parallel execution group."""
        self._parallel_groups[name] = node_names

    # ── Execution ───────────────────────────────────────────────────────

    async def run(self, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the graph from entry to exit.

        Parameters
        ----------
        initial_state:
            Starting state dict.

        Returns
        -------
        Dict[str, Any]
            Final state after execution.
        """
        if self._entry_node is None:
            raise ValueError("No entry node defined")

        state: Dict[str, Any] = dict(initial_state or {})
        state["_errors"] = state.get("_errors", {})
        state["_steps"] = 0
        state["_visited"] = []
        state["_graph_id"] = self.graph_id

        self._status = HarnessGraphStatus.PLANNING
        current_node_name: Optional[str] = self._entry_node
        step_count = 0

        while current_node_name is not None and step_count < self._max_steps:
            # Handle parallel groups
            if current_node_name in self._parallel_groups:
                group = self._parallel_groups[current_node_name]
                group_result = await self._execute_parallel(group, state)
                state.update(group_result)
                step_count += 1
                state["_steps"] = step_count
                state["_visited"].append(current_node_name)
                current_node_name = self._find_next_after_parallel(current_node_name)
                continue

            node = self._nodes.get(current_node_name)
            if node is None:
                logger.warning("Node '%s' not found, stopping", current_node_name)
                break

            # Update graph status based on node role
            if node.role == NodeRole.PLANNER:
                self._status = HarnessGraphStatus.PLANNING
            elif node.role == NodeRole.EXECUTOR:
                self._status = HarnessGraphStatus.EXECUTING
            elif node.role == NodeRole.REVIEWER:
                self._status = HarnessGraphStatus.REVIEWING

            # Execute node with timeout
            step = ExecutionStep(
                node_name=current_node_name,
                role=node.role,
                input_state=copy.deepcopy(state),
            )
            start_time = asyncio.get_event_loop().time()

            try:
                result = await asyncio.wait_for(
                    self._execute_node(node, state),
                    timeout=node.timeout_s,
                )
                if isinstance(result, dict):
                    state.update(result)
                node.status = HarnessNodeStatus.COMPLETED
                step.status = HarnessNodeStatus.COMPLETED
                step.output_state = copy.deepcopy(state)
            except asyncio.TimeoutError:
                node.status = HarnessNodeStatus.FAILED
                node.error = f"Timeout after {node.timeout_s}s"
                step.status = HarnessNodeStatus.FAILED
                step.error = node.error
                state["_errors"][current_node_name] = node.error
            except Exception as e:
                node.status = HarnessNodeStatus.FAILED
                node.error = str(e)
                step.status = HarnessNodeStatus.FAILED
                step.error = str(e)
                state["_errors"][current_node_name] = str(e)

            step.duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self._execution_log.append(step)

            # Handle failures
            if node.status == HarnessNodeStatus.FAILED:
                if current_node_name in self._error_paths:
                    current_node_name = self._error_paths[current_node_name]
                    step_count += 1
                    continue
                else:
                    self._status = HarnessGraphStatus.FAILED
                    return state

            # Check exit
            if current_node_name in self._exit_nodes:
                self._status = HarnessGraphStatus.COMPLETED
                return state

            current_node_name = node.get_next_node(state)
            step_count += 1
            state["_steps"] = step_count
            state["_visited"].append(current_node_name or "")

        if step_count >= self._max_steps:
            self._status = HarnessGraphStatus.FAILED
        else:
            self._status = HarnessGraphStatus.COMPLETED
        return state

    async def _execute_node(
        self, node: HarnessNode, state: Dict[str, Any],
    ) -> Any:
        """Execute a single node's action."""
        if node.action is None:
            return state
        if asyncio.iscoroutinefunction(node.action):
            return await node.action(state)
        return node.action(state)

    async def _execute_parallel(
        self, node_names: List[str], state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute nodes in parallel."""
        tasks: Dict[str, asyncio.Task] = {}
        for name in node_names:
            node = self._nodes.get(name)
            if node and node.action:
                if asyncio.iscoroutinefunction(node.action):
                    tasks[name] = asyncio.create_task(node.action(dict(state)))
                else:
                    tasks[name] = asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(
                            None, node.action, dict(state),
                        )
                    )

        results: Dict[str, Any] = {}
        if tasks:
            done = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for (node_name, _task), result in zip(tasks.items(), done):
                if isinstance(result, Exception):
                    results[node_name] = {"error": str(result)}
                elif isinstance(result, dict):
                    results.update(result)
                else:
                    results[node_name] = result

        return results

    def _find_next_after_parallel(self, group_name: str) -> Optional[str]:
        """Find the next node after a parallel group."""
        group = self._parallel_groups.get(group_name)
        if group is None:
            return None
        group_set = set(group)
        for node_name in group:
            node = self._nodes.get(node_name)
            if node:
                next_node = node.get_next_node({})
                if next_node and next_node not in group_set:
                    return next_node
        return None

    # ── Checkpoint / Resume ─────────────────────────────────────────────

    def checkpoint(self, state: Dict[str, Any], current_node: Optional[str] = None) -> HarnessCheckpoint:
        """Create a checkpoint of the current execution state."""
        node_statuses = {name: node.status for name, node in self._nodes.items()}
        cp = HarnessCheckpoint(
            graph_id=self.graph_id,
            node_statuses=node_statuses,
            state=copy.deepcopy(state),
            current_node=current_node,
            step_count=state.get("_steps", 0),
        )
        self._checkpoints.append(cp)
        return cp

    async def resume(self, checkpoint: HarnessCheckpoint) -> Dict[str, Any]:
        """Resume execution from a checkpoint."""
        for name, status in checkpoint.node_statuses.items():
            if name in self._nodes:
                self._nodes[name].status = status

        state = copy.deepcopy(checkpoint.state)
        self._status = HarnessGraphStatus.EXECUTING

        current_node_name = checkpoint.current_node
        step_count = checkpoint.step_count

        while current_node_name is not None and step_count < self._max_steps:
            node = self._nodes.get(current_node_name)
            if node is None:
                break

            try:
                result = await self._execute_node(node, state)
                if isinstance(result, dict):
                    state.update(result)
                node.status = HarnessNodeStatus.COMPLETED
            except Exception as e:
                node.status = HarnessNodeStatus.FAILED
                state["_errors"][current_node_name] = str(e)
                if current_node_name in self._error_paths:
                    current_node_name = self._error_paths[current_node_name]
                    step_count += 1
                    continue
                self._status = HarnessGraphStatus.FAILED
                return state

            if current_node_name in self._exit_nodes:
                self._status = HarnessGraphStatus.COMPLETED
                return state

            current_node_name = node.get_next_node(state)
            step_count += 1
            state["_steps"] = step_count

        self._status = HarnessGraphStatus.COMPLETED
        return state

    # ── Accessors ───────────────────────────────────────────────────────

    @property
    def status(self) -> HarnessGraphStatus:
        return self._status

    @property
    def nodes(self) -> Dict[str, HarnessNode]:
        return dict(self._nodes)

    @property
    def execution_log(self) -> List[ExecutionStep]:
        return list(self._execution_log)

    @property
    def checkpoints(self) -> List[HarnessCheckpoint]:
        return list(self._checkpoints)

    def get_node(self, name: str) -> Optional[HarnessNode]:
        return self._nodes.get(name)

    def reset(self) -> None:
        """Reset all node statuses and execution state."""
        for node in self._nodes.values():
            node.status = HarnessNodeStatus.PENDING
            node.result = None
            node.error = None
        self._status = HarnessGraphStatus.PENDING
        self._execution_log.clear()
