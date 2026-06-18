"""Pydantic schemas for API requests and responses.

Covers: agents, colonies, tools, memory, and tasks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class AgentCreateRequest(BaseModel):
    """POST /api/v1/agents – create a new agent."""
    agent_type: str
    colony_id: Optional[str] = None
    autonomy_level: int = 1
    capabilities: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentCreateResponse(BaseModel):
    """Response for agent creation."""
    agent_id: str
    agent_type: str
    state: str = "registered"
    colony_id: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """GET /api/v1/agents/{id} – agent status."""
    agent_id: str
    agent_type: str
    state: str
    autonomy_level: int
    colony_id: Optional[str] = None
    health_score: float = 1.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_heartbeat: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class AgentListResponse(BaseModel):
    """GET /api/v1/agents – list agents."""
    agents: List[AgentStatusResponse] = Field(default_factory=list)
    total: int = 0


class AgentExecuteRequest(BaseModel):
    """POST /api/v1/agents/{id}/execute – execute a task on an agent."""
    description: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 2
    timeout_ms: int = 300_000
    required_capabilities: List[str] = Field(default_factory=list)


class AgentExecuteResponse(BaseModel):
    """Response for agent task execution."""
    task_id: str
    agent_id: str
    status: str = "submitted"


class AgentDeleteResponse(BaseModel):
    """DELETE /api/v1/agents/{id} – terminate agent."""
    agent_id: str
    status: str = "terminated"


# ═══════════════════════════════════════════════════════════════════════════════
# COLONY SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class ColonyCreateRequest(BaseModel):
    """POST /api/v1/colonies – create a colony."""
    name: str = "default"
    goal: str = ""
    scale: str = "medium"
    max_agents: int = 50
    routing_strategy: str = "least-loaded"


class ColonyCreateResponse(BaseModel):
    """Response for colony creation."""
    colony_id: str
    name: str
    status: str = "active"
    scale: str = "medium"


class ColonyStatusResponse(BaseModel):
    """GET /api/v1/colonies/{id} – colony status."""
    colony_id: str
    name: str
    goal: str
    status: str
    scale: str = "medium"
    agent_count: int = 0
    task_count: int = 0
    overseer_id: Optional[str] = None
    created_at: Optional[str] = None
    routing_strategy: str = "least-loaded"
    hand_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ColonyListResponse(BaseModel):
    """GET /api/v1/colonies – list colonies."""
    colonies: List[ColonyStatusResponse] = Field(default_factory=list)
    total: int = 0


class ColonyScaleRequest(BaseModel):
    """POST /api/v1/colonies/{id}/scale – scale a colony."""
    scale: str  # micro | small | medium | large


class ColonyScaleResponse(BaseModel):
    """Response for colony scaling."""
    colony_id: str
    scale: str
    max_agents: int
    status: str = "active"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class ToolListResponse(BaseModel):
    """GET /api/v1/tools – list tools."""
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class ToolDescribeResponse(BaseModel):
    """GET /api/v1/tools/{name} – describe a tool."""
    name: str
    category: str = ""
    description: str = ""
    required_autonomy: int = 1
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Dict[str, Any] = Field(default_factory=dict)
    dangerous: bool = False


class ToolCallRequest(BaseModel):
    """POST /api/v1/tools/{name}/call – call a tool."""
    arguments: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str = ""
    autonomy_level: int = 0


class ToolCallResponse(BaseModel):
    """Response for tool invocation."""
    call_id: str
    tool_name: str
    status: str
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryStoreRequest(BaseModel):
    """POST /api/v1/memory/store – store to memory."""
    key: str
    value: Any
    tier: str = "t1_letta"
    agent_id: str = ""
    colony_id: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryStoreResponse(BaseModel):
    """Response for memory store."""
    store_id: str
    status: str = "stored"


class MemoryQueryRequest(BaseModel):
    """POST /api/v1/memory/query – query memory."""
    query: str
    limit: int = 10
    tier: Optional[str] = None
    agent_id: Optional[str] = None
    colony_id: Optional[str] = None


class MemoryQueryResponse(BaseModel):
    """Response for memory query."""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class MemoryCompactRequest(BaseModel):
    """POST /api/v1/memory/compact – trigger compaction."""
    agent_id: Optional[str] = None
    colony_id: Optional[str] = None
    strategy: str = "summary"


class MemoryCompactResponse(BaseModel):
    """Response for memory compaction."""
    status: str = "compacted"
    pages_compacted: int = 0
    tokens_saved: int = 0


class MemoryPagesResponse(BaseModel):
    """GET /api/v1/memory/pages – list pages."""
    pages: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# TASK SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class TaskCreateRequest(BaseModel):
    """POST /api/v1/tasks – create a task."""
    description: str
    colony_id: Optional[str] = None
    priority: int = 2  # 1=low, 2=medium, 3=high, 4=critical
    payload: Dict[str, Any] = Field(default_factory=dict)
    required_capabilities: List[str] = Field(default_factory=list)
    timeout_ms: int = 300_000


class TaskCreateResponse(BaseModel):
    """Response for task creation."""
    task_id: str
    status: str = "pending"
    colony_id: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """GET /api/v1/tasks/{id} – task status."""
    task_id: str
    description: str
    status: str
    priority: int
    assigned_agent: Optional[str] = None
    colony_id: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class TaskResultResponse(BaseModel):
    """GET /api/v1/tasks/{id}/result – task result."""
    task_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    tools_used: List[str] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH / ERROR SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class HealthResponse(BaseModel):
    """GET /health – system health."""
    status: str = "healthy"
    version: str = "0.1.0"
    uptime_seconds: float = 0.0
    agents: int = 0
    colonies: int = 0
    tools: int = 0


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    code: str = "UNKNOWN"
    details: Optional[Dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════


class WSMessage(BaseModel):
    """WebSocket message envelope."""
    type: str  # task_update | heartbeat | alert | log
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = ""


class WSTaskUpdate(BaseModel):
    """WebSocket task update payload."""
    task_id: str
    status: str
    agent_id: Optional[str] = None
    progress: float = 0.0
    message: str = ""


class WSHeartbeat(BaseModel):
    """WebSocket heartbeat payload."""
    agent_id: str
    health_score: float = 1.0
    active_tasks: int = 0


class WSAlert(BaseModel):
    """WebSocket alert payload."""
    level: str  # info | warning | error | critical
    source: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class WSLog(BaseModel):
    """WebSocket log payload."""
    level: str
    agent_id: Optional[str] = None
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
