"""Agent framework for AI-MultiColony.

Exports all agent classes, the registry, event bus, circuit breaker,
graph orchestration, shared state, and Pydantic state models.
"""

from .base import BaseAgent, EventBus, CircuitBreaker, RetryPolicy
from .manus import ManusAgent
from .planner import PlannerAgent
from .executor import ExecutorAgent, SandboxConfig, SandboxHandle
from .coder import CoderAgent, CodeArtifact

# Graceful imports for optional sub-exports
try:
    from .browser import BrowserAgent, BrowserPage
except ImportError:
    from .browser import BrowserAgent
    BrowserPage = None

try:
    from .voice import VoiceAgent, VoiceSession
except ImportError:
    from .voice import VoiceAgent
    VoiceSession = None

from .security import SecurityAgent

try:
    from .researcher import ResearcherAgent, ResearchDocument, ResearchReport
except ImportError:
    from .researcher import ResearcherAgent
    ResearchDocument = None
    ResearchReport = None

try:
    from .colony import ColonyAgent, ColonyMetrics
except ImportError:
    from .colony import ColonyAgent
    ColonyMetrics = None

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
