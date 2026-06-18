"""External framework adapters for AI-MultiColony.

Provides adapters for popular agent frameworks, enabling seamless
integration with CrewAI, AutoGen, and LangGraph ecosystems.

Modules
-------
crewai_adapter   – CrewAI multi-agent crew adapter
autogen_adapter  – AutoGen conversational agent adapter
langgraph_adapter – LangGraph graph orchestration adapter
"""

from .crewai_adapter import (
    CrewAIAdapter,
    CrewAgent,
    CrewTask,
    CrewExecution,
    CrewRole,
    CrewStatus,
    TaskStatus,
)
from .autogen_adapter import (
    AutoGenAdapter,
    AutoGenAgent,
    ChatMessage,
    ConversationResult,
    AutoGenRole,
    ConversationStatus,
)
from .langgraph_adapter import (
    LangGraphAdapter,
    GraphState,
    LangGraphCheckpoint,
    NodeDefinition,
    GraphNodeType,
    ExecutionState,
)

__all__ = [
    # CrewAI
    "CrewAIAdapter",
    "CrewAgent",
    "CrewTask",
    "CrewExecution",
    "CrewRole",
    "CrewStatus",
    "TaskStatus",
    # AutoGen
    "AutoGenAdapter",
    "AutoGenAgent",
    "ChatMessage",
    "ConversationResult",
    "AutoGenRole",
    "ConversationStatus",
    # LangGraph
    "LangGraphAdapter",
    "GraphState",
    "LangGraphCheckpoint",
    "NodeDefinition",
    "GraphNodeType",
    "ExecutionState",
]
