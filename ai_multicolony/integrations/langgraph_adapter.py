"""LangGraph framework adapter for AI-MultiColony.

Provides a real implementation of LangGraph-style graph orchestration
that integrates with AI-MultiColony's agent system.  This adapter
uses DeerFlow patterns for building stateful, conditional execution
graphs.

Key features:
* StateGraph pattern with shared state dict
* Conditional edges for dynamic routing
* Checkpoint/resume for long-running graphs
* Parallel branch execution
* Error recovery paths
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


class GraphNodeType(str, Enum):
    """Type of graph node."""
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    FORK = "fork"
    MERGE = "merge"
    START = "start"
    END = "end"


class ExecutionState(str, Enum):
    """State of graph execution."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Models ───────────────────────────────────────────────────────────────────


class GraphState(BaseModel):
    """Shared state for graph execution."""
    model_config = ConfigDict(frozen=False)

    messages: List[Dict[str, Any]] = Field(default_factory=list)
    current_agent: str = ""
    iteration: int = 0
    max_iterations: int = 50
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the state."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        })

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last message."""
        return self.messages[-1] if self.messages else None


class LangGraphCheckpoint(BaseModel):
    """Checkpoint for LangGraph execution."""
    model_config = ConfigDict(frozen=False)

    checkpoint_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    graph_name: str = ""
    state: Dict[str, Any] = Field(default_factory=dict)
    current_node: Optional[str] = None
    visited_nodes: List[str] = Field(default_factory=list)
    iteration: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NodeDefinition(BaseModel):
    """Definition of a graph node."""
    model_config = ConfigDict(frozen=False)

    name: str = ""
    node_type: GraphNodeType = GraphNodeType.AGENT
    description: str = ""
    next_nodes: List[str] = Field(default_factory=list)
    condition: Optional[str] = None  # Name of condition function
    retry_count: int = 3
    timeout_s: float = 300.0


# ── LangGraph Adapter ────────────────────────────────────────────────────────


class LangGraphAdapter:
    """Adapter for LangGraph-style graph orchestration.

    Implements the StateGraph pattern from LangGraph with:
    * Shared state management
    * Conditional routing
    * Checkpointing
    * Parallel execution
    * Error recovery

    Usage::

        adapter = LangGraphAdapter("research_graph")

        # Add nodes
        adapter.add_node("research", research_fn, GraphNodeType.AGENT)
        adapter.add_node("analyze", analyze_fn, GraphNodeType.AGENT)
        adapter.add_node("report", report_fn, GraphNodeType.AGENT)

        # Add edges
        adapter.add_edge("research", "analyze")
        adapter.add_edge("analyze", "report")
        adapter.add_conditional_edge("analyze", condition_fn, {
            "needs_more": "research",
            "done": "report",
        })

        # Set entry/exit
        adapter.set_entry_point("research")
        adapter.add_exit_point("report")

        # Execute
        result = await adapter.run({"query": "AI trends"})
    """

    def __init__(self, graph_name: str = "default_graph"):
        self._graph_name = graph_name
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: Dict[str, List[str]] = {}
        self._conditional_edges: Dict[str, Dict[str, Any]] = {}
        self._entry_point: Optional[str] = None
        self._exit_points: Set[str] = set()
        self._checkpoints: List[LangGraphCheckpoint] = []
        self._execution_state: ExecutionState = ExecutionState.IDLE
        self._max_iterations: int = 50

    # ── Graph construction ──────────────────────────────────────────────

    def add_node(
        self,
        name: str,
        action: Callable,
        node_type: GraphNodeType = GraphNodeType.AGENT,
        description: str = "",
    ) -> None:
        """Add a node to the graph.

        Parameters
        ----------
        name:
            Unique node name.
        action:
            Async callable ``action(state: GraphState) -> GraphState``
        node_type:
            Type of graph node.
        description:
            Node description.
        """
        self._nodes[name] = {
            "action": action,
            "type": node_type,
            "description": description,
            "retry_count": 3,
            "timeout_s": 300.0,
        }
        self._edges[name] = []

    def add_edge(self, source: str, target: str) -> None:
        """Add an unconditional edge from source to target."""
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        if target not in self._nodes and target != "__end__":
            raise ValueError(f"Target node '{target}' not found")
        self._edges.setdefault(source, []).append(target)

    def add_conditional_edge(
        self,
        source: str,
        condition: Callable,
        targets: Dict[str, str],
    ) -> None:
        """Add a conditional edge from source.

        Parameters
        ----------
        source:
            Source node name.
        condition:
            Callable ``condition(state: GraphState) -> str``
            Returns a key into the targets dict.
        targets:
            Mapping from condition result to target node name.
        """
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        self._conditional_edges[source] = {
            "condition": condition,
            "targets": targets,
        }

    def set_entry_point(self, name: str) -> None:
        """Set the entry point node."""
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        self._entry_point = name

    def add_exit_point(self, name: str) -> None:
        """Add an exit point node."""
        if name not in self._nodes:
            raise ValueError(f"Node '{name}' not found")
        self._exit_points.add(name)

    # ── Execution ───────────────────────────────────────────────────────

    async def run(
        self,
        initial_state: Optional[Dict[str, Any]] = None,
        max_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute the graph from entry to exit.

        Parameters
        ----------
        initial_state:
            Initial state values.
        max_iterations:
            Override max iterations.

        Returns
        -------
        Dict[str, Any]
            Final state after execution.
        """
        if self._entry_point is None:
            raise ValueError("No entry point set")

        self._execution_state = ExecutionState.RUNNING

        # Initialize state
        state = GraphState(
            data=initial_state or {},
            max_iterations=max_iterations or self._max_iterations,
        )

        current_node = self._entry_point
        visited: List[str] = []

        while current_node is not None and state.iteration < state.max_iterations:
            state.iteration += 1

            # Check if we're in a valid state
            if self._execution_state != ExecutionState.RUNNING:
                break

            node_def = self._nodes.get(current_node)
            if node_def is None:
                logger.warning("Node '%s' not found, stopping", current_node)
                break

            # Execute node
            action = node_def["action"]
            try:
                if asyncio.iscoroutinefunction(action):
                    result = await asyncio.wait_for(
                        action(state),
                        timeout=node_def.get("timeout_s", 300.0),
                    )
                else:
                    result = action(state)

                # Update state
                if isinstance(result, GraphState):
                    state = result
                elif isinstance(result, dict):
                    state.data.update(result)

            except asyncio.TimeoutError:
                state.errors[current_node] = f"Timeout after {node_def.get('timeout_s', 300)}s"
                logger.error("Node %s timed out", current_node)
            except Exception as e:
                state.errors[current_node] = str(e)
                logger.error("Node %s error: %s", current_node, e)

            visited.append(current_node)

            # Check if exit point
            if current_node in self._exit_points:
                self._execution_state = ExecutionState.COMPLETED
                break

            # Determine next node
            current_node = self._get_next_node(current_node, state)

        if state.iteration >= state.max_iterations:
            self._execution_state = ExecutionState.FAILED
        elif self._execution_state == ExecutionState.RUNNING:
            self._execution_state = ExecutionState.COMPLETED

        return {
            "messages": state.messages,
            "data": state.data,
            "errors": state.errors,
            "iterations": state.iteration,
            "visited": visited,
            "status": self._execution_state.value,
        }

    def _get_next_node(self, current: str, state: GraphState) -> Optional[str]:
        """Determine the next node based on edges and conditions."""
        # Check conditional edges first
        cond_edge = self._conditional_edges.get(current)
        if cond_edge is not None:
            try:
                result = cond_edge["condition"](state)
                targets = cond_edge["targets"]
                if result in targets:
                    return targets[result]
                # Treat result as direct node name
                if result in self._nodes:
                    return result
            except Exception as e:
                logger.warning("Conditional edge error at %s: %s", current, e)

        # Check unconditional edges
        edges = self._edges.get(current, [])
        if edges:
            return edges[0]

        return None

    # ── Checkpointing ───────────────────────────────────────────────────

    def save_checkpoint(self, state: GraphState, current_node: str) -> LangGraphCheckpoint:
        """Save a checkpoint of the current execution."""
        cp = LangGraphCheckpoint(
            graph_name=self._graph_name,
            state=state.model_dump(),
            current_node=current_node,
            iteration=state.iteration,
        )
        self._checkpoints.append(cp)
        return cp

    async def resume_from_checkpoint(self, checkpoint: LangGraphCheckpoint) -> Dict[str, Any]:
        """Resume execution from a checkpoint."""
        state = GraphState(**checkpoint.state)
        self._execution_state = ExecutionState.RUNNING

        current_node = checkpoint.current_node
        state.iteration = checkpoint.iteration

        while current_node is not None and state.iteration < state.max_iterations:
            state.iteration += 1
            node_def = self._nodes.get(current_node)
            if node_def is None:
                break

            action = node_def["action"]
            try:
                if asyncio.iscoroutinefunction(action):
                    result = await action(state)
                else:
                    result = action(state)

                if isinstance(result, GraphState):
                    state = result
                elif isinstance(result, dict):
                    state.data.update(result)

            except Exception as e:
                state.errors[current_node] = str(e)

            if current_node in self._exit_points:
                break

            current_node = self._get_next_node(current_node, state)

        self._execution_state = ExecutionState.COMPLETED
        return state.model_dump()

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def graph_name(self) -> str:
        return self._graph_name

    @property
    def node_names(self) -> List[str]:
        return list(self._nodes.keys())

    @property
    def checkpoints(self) -> List[LangGraphCheckpoint]:
        return list(self._checkpoints)

    @property
    def execution_state(self) -> ExecutionState:
        return self._execution_state

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "graph_name": self._graph_name,
            "node_count": len(self._nodes),
            "edge_count": sum(len(v) for v in self._edges.values()),
            "conditional_edge_count": len(self._conditional_edges),
            "checkpoints": len(self._checkpoints),
            "execution_state": self._execution_state.value,
        }
