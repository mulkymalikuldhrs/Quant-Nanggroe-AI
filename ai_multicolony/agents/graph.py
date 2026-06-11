"""Agent graph – LangGraph-style graph orchestration.

Provides a :class:`StateGraph` for building agent workflows with
conditional edges, parallel branch execution, checkpoint/resume support,
and error recovery paths.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Graph types ──


class NodeStatus(str, Enum):
    """Execution status of a graph node."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GraphStatus(str, Enum):
    """Execution status of the entire graph."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


# ── Checkpoint ──


class GraphCheckpoint(BaseModel):
    """Serializable checkpoint of graph execution state.

    Stores the node statuses, current state dict, and metadata so that
    execution can be resumed after a pause or crash.
    """

    model_config = ConfigDict(frozen=False)

    checkpoint_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    graph_id: str = ""
    node_statuses: Dict[str, NodeStatus] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)
    current_node: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    step_count: int = 0


# ── Node ──


class GraphNode:
    """A node in the agent workflow graph.

    Each node wraps an async callable (the *action*) that receives and
    returns a state dict.  Nodes may declare conditional edges to other
    nodes, enabling dynamic routing.
    """

    def __init__(
        self,
        name: str,
        action: Optional[Callable[..., Any]] = None,
        is_entry: bool = False,
        is_exit: bool = False,
    ):
        self.name = name
        self.action = action
        self.is_entry = is_entry
        self.is_exit = is_exit
        self.status: NodeStatus = NodeStatus.PENDING
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self._edges: List[GraphEdge] = []
        self._conditional_edges: List[ConditionalEdge] = []
        self._retry_count: int = 0
        self._max_retries: int = 3

    def add_edge(self, target: str) -> None:
        """Add an unconditional edge to *target*."""
        self._edges.append(GraphEdge(source=self.name, target=target))

    def add_conditional_edge(
        self,
        condition: Callable[[Dict[str, Any]], str],
        targets: Optional[Dict[str, str]] = None,
    ) -> None:
        """Add a conditional edge.

        *condition* is a callable that receives the state dict and returns
        the name of the next node.  If *targets* is provided, the return
        value is used as a key into *targets* to resolve the actual node
        name.
        """
        self._conditional_edges.append(ConditionalEdge(
            source=self.name, condition=condition, targets=targets or {},
        ))

    def get_next_node(self, state: Dict[str, Any]) -> Optional[str]:
        """Determine the next node based on current state.

        Checks conditional edges first; falls back to the first
        unconditional edge; returns ``None`` for terminal nodes.
        """
        # Conditional edges take priority
        for cond_edge in self._conditional_edges:
            try:
                result = cond_edge.condition(state)
                if result in cond_edge.targets:
                    return cond_edge.targets[result]
                return result  # treat result as a direct node name
            except Exception as e:
                logger.warning(f"Conditional edge error in {self.name}: {e}")
                continue

        # Unconditional edges
        if self._edges:
            return self._edges[0].target

        return None


class GraphEdge:
    """Unconditional directed edge between two nodes."""

    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target


class ConditionalEdge:
    """Conditional directed edge with a routing function."""

    def __init__(
        self,
        source: str,
        condition: Callable[[Dict[str, Any]], str],
        targets: Dict[str, str],
    ):
        self.source = source
        self.condition = condition
        self.targets = targets


# ── Parallel Branch ──


class ParallelBranch:
    """A set of nodes that can execute concurrently.

    All nodes in the branch receive the same input state; their results
    are merged before the branch converges to a single successor node.
    """

    def __init__(self, name: str, node_names: List[str], merge_action: Optional[Callable] = None):
        self.name = name
        self.node_names = node_names
        self.merge_action = merge_action or self._default_merge

    @staticmethod
    def _default_merge(results: Dict[str, Any]) -> Dict[str, Any]:
        """Default merge: flatten all result dicts into one."""
        merged: Dict[str, Any] = {}
        for node_name, result in results.items():
            if isinstance(result, dict):
                merged.update(result)
            else:
                merged[node_name] = result
        return merged


# ── StateGraph ──


class AgentGraph:
    """LangGraph-style graph orchestration for agent workflows.

    Features
    --------
    * **StateGraph** pattern – nodes transform a shared state dict.
    * **Conditional edges** – route to different nodes based on state.
    * **Parallel branch execution** – run multiple nodes concurrently.
    * **Checkpoint / resume** – serialize and restore execution state.
    * **Error recovery paths** – define fallback nodes on failure.

    Usage
    -----
    ::

        graph = AgentGraph("my_workflow")
        graph.add_node("start", start_action, entry=True)
        graph.add_node("process", process_action)
        graph.add_node("end", end_action, exit=True)
        graph.add_edge("start", "process")
        graph.add_edge("process", "end")

        result = await graph.run({"input": "hello"})
    """

    def __init__(self, graph_id: str = ""):
        self.graph_id = graph_id or f"graph-{uuid.uuid4().hex[:8]}"
        self._nodes: Dict[str, GraphNode] = {}
        self._entry_node: Optional[str] = None
        self._exit_nodes: Set[str] = set()
        self._parallel_branches: Dict[str, ParallelBranch] = {}
        self._error_paths: Dict[str, str] = {}  # node_name → fallback_node_name
        self._status: GraphStatus = GraphStatus.PENDING
        self._checkpoints: List[GraphCheckpoint] = []
        self._execution_log: List[Dict[str, Any]] = []
        self._max_steps: int = 100

    # ── Graph construction ──

    def add_node(
        self,
        name: str,
        action: Optional[Callable[..., Any]] = None,
        entry: bool = False,
        exit: bool = False,
    ) -> GraphNode:
        """Add a node to the graph.

        Parameters
        ----------
        name:
            Unique node name.
        action:
            Async callable ``action(state) -> state``.
        entry:
            Mark as the entry point (one per graph).
        exit:
            Mark as a terminal / exit node.
        """
        node = GraphNode(name=name, action=action, is_entry=entry, is_exit=exit)
        self._nodes[name] = node
        if entry:
            self._entry_node = name
        if exit:
            self._exit_nodes.add(name)
        return node

    def add_edge(self, source: str, target: str) -> None:
        """Add an unconditional edge from *source* to *target*.

        *target* may be a regular node name or a parallel branch name.
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        # Allow target to be a parallel branch name or a regular node
        if target not in self._nodes and target not in self._parallel_branches:
            raise ValueError(f"Target node '{target}' not found")
        self._nodes[source].add_edge(target)

    def add_conditional_edge(
        self,
        source: str,
        condition: Callable[[Dict[str, Any]], str],
        targets: Optional[Dict[str, str]] = None,
    ) -> None:
        """Add a conditional edge from *source*.

        *condition* is called with the current state dict after *source*
        executes.  Its return value determines the next node.
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        self._nodes[source].add_conditional_edge(condition, targets)

    def add_parallel_branch(
        self,
        name: str,
        node_names: List[str],
        merge_action: Optional[Callable] = None,
    ) -> None:
        """Register a parallel branch.

        When a node transitions to a parallel branch, all nodes in the
        branch execute concurrently and their results are merged.
        """
        self._parallel_branches[name] = ParallelBranch(
            name=name, node_names=node_names, merge_action=merge_action,
        )

    def add_error_path(self, node_name: str, fallback_node: str) -> None:
        """Define a fallback node when *node_name* fails.

        Instead of aborting the graph, execution continues at
        *fallback_node* with the error stored in ``state["_errors"]``.
        """
        self._error_paths[node_name] = fallback_node

    # ── Execution ──

    async def run(self, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the graph from the entry node to an exit node.

        Parameters
        ----------
        initial_state:
            Starting state dict (empty dict if not provided).

        Returns
        -------
        Dict[str, Any]
            The final state after execution completes.
        """
        if self._entry_node is None:
            raise ValueError("No entry node defined")

        state: Dict[str, Any] = dict(initial_state or {})
        self._status = GraphStatus.RUNNING
        state["_errors"] = state.get("_errors", {})
        state["_steps"] = 0
        state["_visited"] = []

        current_node_name: Optional[str] = self._entry_node
        step_count = 0

        while current_node_name is not None and step_count < self._max_steps:
            # Check for parallel branch
            if current_node_name in self._parallel_branches:
                branch = self._parallel_branches[current_node_name]
                branch_result = await self._execute_parallel_branch(branch, state)
                state.update(branch_result)
                step_count += 1
                state["_steps"] = step_count
                state["_visited"].append(current_node_name)
                # After parallel branch, determine next node
                current_node_name = self._find_post_branch_target(current_node_name)
                continue

            node = self._nodes.get(current_node_name)
            if node is None:
                logger.warning(f"Node '{current_node_name}' not found, stopping")
                break

            # Execute node
            node.status = NodeStatus.RUNNING
            self._execution_log.append({
                "node": current_node_name,
                "status": "running",
                "step": step_count,
                "timestamp": datetime.utcnow().isoformat(),
            })

            try:
                if node.action is not None:
                    if asyncio.iscoroutinefunction(node.action):
                        result = await node.action(state)
                    else:
                        result = node.action(state)
                    if isinstance(result, dict):
                        state.update(result)
                node.status = NodeStatus.COMPLETED
                node.result = state
            except Exception as e:
                node.status = NodeStatus.FAILED
                node.error = str(e)
                state["_errors"][current_node_name] = str(e)
                self._execution_log.append({
                    "node": current_node_name,
                    "status": "failed",
                    "error": str(e),
                    "step": step_count,
                })

                # Error recovery
                if current_node_name in self._error_paths:
                    current_node_name = self._error_paths[current_node_name]
                    step_count += 1
                    continue
                else:
                    self._status = GraphStatus.FAILED
                    return state

            self._execution_log.append({
                "node": current_node_name,
                "status": "completed",
                "step": step_count,
            })

            # Check if exit node
            if node.is_exit:
                self._status = GraphStatus.COMPLETED
                return state

            # Determine next node
            current_node_name = node.get_next_node(state)
            step_count += 1
            state["_steps"] = step_count
            state["_visited"].append(node.name)

        self._status = GraphStatus.COMPLETED if step_count < self._max_steps else GraphStatus.FAILED
        return state

    async def _execute_parallel_branch(
        self,
        branch: ParallelBranch,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute all nodes in a parallel branch concurrently."""
        tasks: Dict[str, asyncio.Task] = {}
        for node_name in branch.node_names:
            node = self._nodes.get(node_name)
            if node and node.action:
                if asyncio.iscoroutinefunction(node.action):
                    tasks[node_name] = asyncio.create_task(node.action(dict(state)))
                else:
                    tasks[node_name] = asyncio.create_task(
                        asyncio.coroutine(lambda n=node: n.action(dict(state)))()
                    )

        results: Dict[str, Any] = {}
        if tasks:
            done = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for (node_name, _task), result in zip(tasks.items(), done):
                if isinstance(result, Exception):
                    results[node_name] = {"error": str(result)}
                else:
                    results[node_name] = result

        return branch.merge_action(results)

    def _find_post_branch_target(self, branch_name: str) -> Optional[str]:
        """Find the next node after a parallel branch completes.

        Returns the first node that isn't part of the branch, searching
        from edges of branch member nodes.
        """
        branch = self._parallel_branches.get(branch_name)
        if branch is None:
            return None

        branch_set = set(branch.node_names)
        for node_name in branch.node_names:
            node = self._nodes.get(node_name)
            if node:
                next_node = node.get_next_node({})
                if next_node and next_node not in branch_set:
                    return next_node

        return None

    # ── Checkpoint / Resume ──

    def checkpoint(self, state: Dict[str, Any], current_node: Optional[str] = None) -> GraphCheckpoint:
        """Create a checkpoint of the current execution state.

        Serializes node statuses, the state dict, and the current node
        so that execution can be resumed later.
        """
        node_statuses = {
            name: node.status for name, node in self._nodes.items()
        }
        cp = GraphCheckpoint(
            graph_id=self.graph_id,
            node_statuses=node_statuses,
            state=copy.deepcopy(state),
            current_node=current_node,
            step_count=state.get("_steps", 0),
        )
        self._checkpoints.append(cp)
        return cp

    async def resume(self, checkpoint: GraphCheckpoint) -> Dict[str, Any]:
        """Resume execution from a checkpoint.

        Restores node statuses and state, then continues execution from
        the node that was current when the checkpoint was taken.
        """
        # Restore node statuses
        for name, status in checkpoint.node_statuses.items():
            if name in self._nodes:
                self._nodes[name].status = status

        # Restore state
        state = copy.deepcopy(checkpoint.state)
        self._status = GraphStatus.RUNNING

        # Continue from current node
        current_node_name = checkpoint.current_node
        step_count = checkpoint.step_count

        while current_node_name is not None and step_count < self._max_steps:
            node = self._nodes.get(current_node_name)
            if node is None:
                break

            node.status = NodeStatus.RUNNING
            try:
                if node.action is not None:
                    if asyncio.iscoroutinefunction(node.action):
                        result = await node.action(state)
                    else:
                        result = node.action(state)
                    if isinstance(result, dict):
                        state.update(result)
                node.status = NodeStatus.COMPLETED
            except Exception as e:
                node.status = NodeStatus.FAILED
                state["_errors"] = state.get("_errors", {})
                state["_errors"][current_node_name] = str(e)
                if current_node_name in self._error_paths:
                    current_node_name = self._error_paths[current_node_name]
                    step_count += 1
                    continue
                self._status = GraphStatus.FAILED
                return state

            if node.is_exit:
                self._status = GraphStatus.COMPLETED
                return state

            current_node_name = node.get_next_node(state)
            step_count += 1
            state["_steps"] = step_count

        self._status = GraphStatus.COMPLETED
        return state

    async def pause(self, state: Dict[str, Any], current_node: Optional[str] = None) -> GraphCheckpoint:
        """Pause execution and return a checkpoint.

        The graph status is set to ``PAUSED`` and a checkpoint is created
        that can be used with :meth:`resume` later.
        """
        self._status = GraphStatus.PAUSED
        return self.checkpoint(state, current_node)

    # ── Accessors ──

    @property
    def status(self) -> GraphStatus:
        """Current graph execution status."""
        return self._status

    @property
    def nodes(self) -> Dict[str, GraphNode]:
        """All nodes in the graph."""
        return dict(self._nodes)

    @property
    def execution_log(self) -> List[Dict[str, Any]]:
        """Log of all node executions."""
        return list(self._execution_log)

    @property
    def checkpoints(self) -> List[GraphCheckpoint]:
        """All saved checkpoints."""
        return list(self._checkpoints)

    def get_node(self, name: str) -> Optional[GraphNode]:
        """Look up a node by name."""
        return self._nodes.get(name)

    def reset(self) -> None:
        """Reset all node statuses and execution state."""
        for node in self._nodes.values():
            node.status = NodeStatus.PENDING
            node.result = None
            node.error = None
        self._status = GraphStatus.PENDING
        self._execution_log.clear()
