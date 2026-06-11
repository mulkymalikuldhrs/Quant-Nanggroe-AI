"""API route handlers for AI-MultiColony."""

from .agents import AgentRoutes
from .colony import ColonyRoutes
from .tools import ToolRoutes
from .memory import MemoryRoutes
from .tasks import TaskRoutes
from .ws import WebSocketHandler

__all__ = [
    "AgentRoutes",
    "ColonyRoutes",
    "ToolRoutes",
    "MemoryRoutes",
    "TaskRoutes",
    "WebSocketHandler",
]
