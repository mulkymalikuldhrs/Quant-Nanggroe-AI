"""Agent framework for AI-MultiColony.

Exports all agent classes, the registry, event bus, circuit breaker,
graph orchestration, shared state, and Pydantic state models.
"""

from .base import BaseAgent, EventBus, CircuitBreaker, RetryPolicy
from .manus import ManusAgent
from .planner import PlannerAgent
from .executor import ExecutorAgent, SandboxConfig, SandboxHandle
from .coder import CoderAgent, CodeArtifact
from .browser import BrowserAgent, BrowserPage
from .voice import VoiceAgent, VoiceSession
from .security import SecurityAgent
from .researcher import ResearcherAgent, ResearchDocument, ResearchReport
from .colony import ColonyAgent, ColonyMetrics
from .graph import AgentGraph, GraphNode, GraphEdge, ConditionalEdge, ParallelBranch, GraphCheckpoint
from .registry import AgentRegistry, AGENT_TYPES
from .state import (
    SharedAgentState,
    AgentStateModel,
    AgentConfig,
    ColonyState,
    TaskStateModel,
    A2AMessageState,
    HealthReport,
)

__all__ = [
    # Base
    "BaseAgent", "EventBus", "CircuitBreaker", "RetryPolicy",
    # Agents
    "ManusAgent", "PlannerAgent", "ExecutorAgent",
    "CoderAgent", "BrowserAgent", "VoiceAgent",
    "SecurityAgent", "ResearcherAgent", "ColonyAgent",
    # Executor helpers
    "SandboxConfig", "SandboxHandle",
    # Coder helpers
    "CodeArtifact",
    # Browser helpers
    "BrowserPage",
    # Voice helpers
    "VoiceSession",
    # Researcher helpers
    "ResearchDocument", "ResearchReport",
    # Colony helpers
    "ColonyMetrics",
    # Graph
    "AgentGraph", "GraphNode", "GraphEdge", "ConditionalEdge",
    "ParallelBranch", "GraphCheckpoint",
    # Registry
    "AgentRegistry", "AGENT_TYPES",
    # State
    "SharedAgentState", "AgentStateModel", "AgentConfig",
    "ColonyState", "TaskStateModel", "A2AMessageState", "HealthReport",
]
