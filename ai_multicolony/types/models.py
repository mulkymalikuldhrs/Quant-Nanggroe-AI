"""Pydantic v2 models and enums for the AI-MultiColony ecosystem.

This module contains every type definition used across the system,
organized by domain: agents, colonies, tasks, tools, MCP, memory,
security, A2A, channels, and API.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


def _uid() -> str:
    """Generate a short unique identifier."""
    return uuid4().hex[:12]


def _now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class AgentType(str, enum.Enum):
    """Types of agents in the ecosystem."""
    MANUS = "manus"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CODER = "coder"
    BROWSER = "browser"
    VOICE = "voice"
    SECURITY = "security"
    RESEARCHER = "researcher"
    COLONY = "colony"


class AgentState(str, enum.Enum):
    """Lifecycle states of an agent."""
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    WAITING = "waiting"
    COMPACTING = "compacting"
    DRAINING = "draining"
    TERMINATED = "terminated"


class AutonomyLevel(int, enum.Enum):
    """Autonomy levels controlling what actions an agent may take.

    L0 – Read-only, no side effects.
    L1 – Safe operations (search, read files).
    L2 – Moderate (write files, run tests).
    L3 – Sensitive (deploy, network calls).
    L4 – Destructive (delete resources, shell access).
    """
    L0_READONLY = 0
    L1_SAFE_OPS = 1
    L2_MODERATE = 2
    L3_SENSITIVE = 3
    L4_DESTRUCTIVE = 4


class ColonyStatus(str, enum.Enum):
    """Lifecycle states of a colony."""
    CREATING = "creating"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class TaskStatus(str, enum.Enum):
    """Lifecycle states of a task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    TIMED_OUT = "timed_out"


class TaskPriority(int, enum.Enum):
    """Task priority levels."""
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class ToolCategory(str, enum.Enum):
    """Categories of tools available to agents."""
    BROWSER = "browser"
    VCS = "vcs"
    API = "api"
    SANDBOX = "sandbox"
    MEMORY = "memory"
    COMPUTE = "compute"
    COMMUNICATION = "communication"
    DATA = "data"
    SECURITY = "security"
    VOICE = "voice"
    DESKTOP = "desktop"
    KNOWLEDGE = "knowledge"


class MemoryTier(str, enum.Enum):
    """Memory storage tiers."""
    T0_CONTEXT = "t0_context"
    T1_LETTA = "t1_letta"
    T2_VECTOR = "t2_vector"
    T3_TEMPORAL = "t3_temporal"
    T4_TREE = "t4_tree"


class HandType(str, enum.Enum):
    """The 7 specialist hand types in a colony."""
    SECURITY = "security"
    CODE = "code"
    RESEARCH = "research"
    BROWSER = "browser"
    VOICE = "voice"
    COMPUTE = "compute"
    INTEGRATION = "integration"


class EventType(str, enum.Enum):
    """Event types emitted by the event bus."""
    AGENT_SPAWNED = "agent_spawned"
    AGENT_TERMINATED = "agent_terminated"
    AGENT_STATE_CHANGED = "agent_state_changed"
    TASK_SUBMITTED = "task_submitted"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    MEMORY_STORED = "memory_stored"
    MEMORY_RETRIEVED = "memory_retrieved"
    MEMORY_COMPACTED = "memory_compacted"
    COLONY_CREATED = "colony_created"
    COLONY_SHUTDOWN = "colony_shutdown"
    A2A_MESSAGE = "a2a_message"
    HEARTBEAT = "heartbeat"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    SECURITY_ALERT = "security_alert"
    CHANNEL_MESSAGE = "channel_message"


class CondenserType(str, enum.Enum):
    """Memory condenser strategies."""
    SUMMARY = "summary"
    EXTRACTION = "extraction"
    TEMPORAL = "temporal"
    ROLLUP = "rollup"
    DEDUPLICATION = "deduplication"
    PRIORITY = "priority"
    SLIDING_WINDOW = "sliding_window"
    HIERARCHICAL = "hierarchical"


class AuditLevel(str, enum.Enum):
    """Audit logging verbosity levels."""
    MINIMAL = "minimal"
    SUMMARY = "summary"
    FULL = "full"


class AuditEventType(str, enum.Enum):
    """Types of auditable events."""
    TOOL_CALL = "tool_call"
    AUTH = "auth"
    CREDENTIAL_ACCESS = "credential_access"
    ESCALATION = "escalation"
    COLONY_CHANGE = "colony_change"
    PERMISSION_CHECK = "permission_check"
    APPROVAL_GRANT = "approval_grant"
    APPROVAL_DENY = "approval_deny"
    AGENT_ACTION = "agent_action"


class MessageFormat(str, enum.Enum):
    """Message format types for channels."""
    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"


class A2AMessageType(str, enum.Enum):
    """Agent-to-Agent message types."""
    TASK_DELEGATION = "task_delegation"
    QUERY = "query"
    RESULT = "result"
    HEARTBEAT = "heartbeat"
    CAPABILITY_AD = "capability_ad"
    ERROR = "error"
    HANDSHAKE_INIT = "handshake_init"
    HANDSHAKE_ACK = "handshake_ack"
    HANDSHAKE_COMPLETE = "handshake_complete"


class ColonyScale(str, enum.Enum):
    """Colony sizing presets."""
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class RoutingStrategy(str, enum.Enum):
    """Task routing strategies."""
    LEAST_LOADED = "least-loaded"
    ROUND_ROBIN = "round-robin"
    CAPABILITY_MATCH = "capability-match"


class CircuitBreakerState(str, enum.Enum):
    """Circuit breaker states for fault tolerance."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ChannelType(str, enum.Enum):
    """Supported communication channel types."""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    SLACK = "slack"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class AgentCapabilities(BaseModel):
    """Declares what an agent can do."""
    tools: List[str] = Field(default_factory=list, description="Tool names the agent can use")
    skills: List[str] = Field(default_factory=list, description="Skill names the agent possesses")
    languages: List[str] = Field(default_factory=list, description="Programming languages")
    max_concurrent_tasks: int = Field(default=3, description="Max parallel tasks")
    supports_streaming: bool = Field(default=False)
    supports_multimodal: bool = Field(default=False)


class AgentSpec(BaseModel):
    """Specification for creating a new agent."""
    model_config = ConfigDict(frozen=False)

    agent_id: str = Field(default_factory=_uid)
    agent_type: AgentType = AgentType.MANUS
    autonomy_level: AutonomyLevel = AutonomyLevel.L1_SAFE_OPS
    colony_id: Optional[str] = None
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    required_tools: List[str] = Field(default_factory=list)
    skill_bindings: List[str] = Field(default_factory=list)
    heartbeat_interval_ms: int = 30_000
    timeout_ms: int = 300_000
    max_retries: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentInfo(BaseModel):
    """Runtime information about an agent."""
    agent_id: str
    agent_type: AgentType
    state: AgentState = AgentState.REGISTERED
    autonomy_level: AutonomyLevel = AutonomyLevel.L1_SAFE_OPS
    colony_id: Optional[str] = None
    health_score: float = 1.0
    created_at: datetime = Field(default_factory=_now)
    last_heartbeat: Optional[datetime] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_task_id: Optional[str] = None
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)


# ═══════════════════════════════════════════════════════════════════════════════
# COLONY TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class HandConfig(BaseModel):
    """Configuration for a single hand (specialist group)."""
    hand_type: HandType
    min_replicas: int = 1
    max_replicas: int = 10
    description: str = ""
    scaling_policy: str = "manual"  # manual | auto
    target_cpu_pct: float = 70.0
    target_task_queue_depth: int = 5


class ColonyConfig(BaseModel):
    """Configuration for creating a new colony."""
    colony_id: str = Field(default_factory=_uid)
    name: str = "default"
    goal: str = ""
    scale: ColonyScale = ColonyScale.MEDIUM
    routing_strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED
    heartbeat_interval_ms: int = 30_000
    default_autonomy: AutonomyLevel = AutonomyLevel.L1_SAFE_OPS
    a2a_enabled: bool = True
    inter_colony: bool = True
    skill_sharing: bool = True
    max_agents: int = 50
    hands: Dict[str, Dict[str, int]] = Field(default_factory=lambda: {
        "security": {"min": 1, "max": 5},
        "code": {"min": 2, "max": 10},
        "research": {"min": 1, "max": 5},
        "browser": {"min": 2, "max": 10},
        "voice": {"min": 0, "max": 3},
        "compute": {"min": 3, "max": 20},
        "integration": {"min": 1, "max": 5},
    })
    resource_limits: Dict[str, Any] = Field(default_factory=lambda: {
        "cpu": "2",
        "memory": "4Gi",
        "max_concurrent_tasks": 20,
    })


class ColonyInfo(BaseModel):
    """Runtime information about a colony."""
    colony_id: str
    name: str
    goal: str
    status: ColonyStatus = ColonyStatus.CREATING
    scale: ColonyScale = ColonyScale.MEDIUM
    agent_count: int = 0
    task_count: int = 0
    overseer_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    routing_strategy: RoutingStrategy = RoutingStrategy.LEAST_LOADED
    hand_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ColonyHealth(BaseModel):
    """Health assessment of a colony."""
    colony_id: str
    overall_score: float = 1.0
    agent_health_avg: float = 1.0
    task_success_rate: float = 1.0
    hand_coverage: float = 1.0
    resource_utilization: float = 0.0
    last_heartbeat: Optional[datetime] = None
    issues: List[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=_now)


# ═══════════════════════════════════════════════════════════════════════════════
# TASK TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class TaskDeadline(BaseModel):
    """Deadline specification for a task."""
    absolute: Optional[datetime] = None
    relative_ms: Optional[int] = None
    enforced: bool = True


class Task(BaseModel):
    """A unit of work to be executed by an agent."""
    model_config = ConfigDict(frozen=False)

    task_id: str = Field(default_factory=_uid)
    description: str = ""
    assigned_agent: Optional[str] = None
    colony_id: Optional[str] = None
    hand_type: Optional[HandType] = None
    parent_task_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    deadline: Optional[TaskDeadline] = None
    required_capabilities: List[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    retry_delay_ms: int = 1000
    timeout_ms: int = 300_000
    created_at: datetime = Field(default_factory=_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskResult(BaseModel):
    """Result of a completed task."""
    task_id: str
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    tools_used: List[str] = Field(default_factory=list)
    agent_id: Optional[str] = None
    colony_id: Optional[str] = None
    retry_count: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class ToolSpec(BaseModel):
    """Specification of a tool."""
    name: str
    category: ToolCategory
    description: str = ""
    required_autonomy: AutonomyLevel = AutonomyLevel.L1_SAFE_OPS
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Dict[str, Any] = Field(default_factory=dict)
    rate_limit_rpm: int = 60
    timeout_ms: int = 30_000
    dangerous: bool = False


class ToolCall(BaseModel):
    """A tool invocation request."""
    call_id: str = Field(default_factory=_uid)
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None
    colony_id: Optional[str] = None
    autonomy_level: AutonomyLevel = AutonomyLevel.L1_SAFE_OPS
    session_id: Optional[str] = None


class ToolResult(BaseModel):
    """Result of a tool invocation."""
    call_id: str
    tool_name: str
    status: str = "success"
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    audit_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# MCP MESSAGE TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class MCPRequest(BaseModel):
    """JSON-RPC style MCP request."""
    jsonrpc: str = "2.0"
    id: str = Field(default_factory=_uid)
    method: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


class MCPResponse(BaseModel):
    """JSON-RPC style MCP response."""
    jsonrpc: str = "2.0"
    id: str = ""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPNotification(BaseModel):
    """MCP server-sent notification."""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryPage(BaseModel):
    """A page of agent context in the Letta-style paging system."""
    page_id: str = Field(default_factory=_uid)
    agent_id: str = ""
    colony_id: str = ""
    session_id: str = ""
    page_number: int = 0
    created_at: datetime = Field(default_factory=_now)
    token_count: int = 0
    summary: str = ""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    key_facts: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_compacted: bool = False


class TemporalFact(BaseModel):
    """A time-bounded fact in the temporal knowledge graph."""
    fact_id: str = Field(default_factory=_uid)
    subject: str = ""
    predicate: str = ""
    obj: str = ""
    valid_from: datetime = Field(default_factory=_now)
    valid_to: Optional[datetime] = None
    confidence: float = 1.0
    source: Dict[str, Any] = Field(default_factory=dict)


class TreeNode(BaseModel):
    """A node in the hierarchical tree memory."""
    node_id: str = Field(default_factory=_uid)
    parent_id: Optional[str] = None
    path: str = "/"
    node_type: str = "generic"
    content: Dict[str, Any] = Field(default_factory=dict)
    children: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    access_count: int = 0


class FactQuery(BaseModel):
    """A query against the temporal knowledge graph."""
    subject: Optional[str] = None
    predicate: Optional[str] = None
    obj: Optional[str] = None
    at_time: Optional[datetime] = None
    min_confidence: float = 0.0
    limit: int = 100


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class AuditEntry(BaseModel):
    """A single entry in the audit trail (Merkle hash-chain)."""
    entry_id: str = Field(default_factory=_uid)
    agent_id: str = ""
    colony_id: str = ""
    tool_name: str = ""
    action: str = ""
    autonomy_level: AutonomyLevel = AutonomyLevel.L0_READONLY
    approved: bool = True
    timestamp: datetime = Field(default_factory=_now)
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    """Structured audit event with full context."""
    event_id: str = Field(default_factory=_uid)
    event_type: AuditEventType
    agent_id: str = ""
    colony_id: str = ""
    timestamp: datetime = Field(default_factory=_now)
    level: AuditLevel = AuditLevel.FULL
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_id: Optional[str] = None


class AuditQuery(BaseModel):
    """Query parameters for filtering audit entries."""
    agent_id: Optional[str] = None
    colony_id: Optional[str] = None
    event_type: Optional[AuditEventType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    level: Optional[AuditLevel] = None
    approved_only: bool = False
    limit: int = 100
    offset: int = 0


class RoleDef(BaseModel):
    """RBAC role definition."""
    name: str
    autonomy_level: AutonomyLevel = AutonomyLevel.L1_SAFE_OPS
    allowed_tools: List[str] = Field(default_factory=list)  # "*" means all
    allowed_actions: List[str] = Field(default_factory=list)
    description: str = ""
    is_default: bool = False


class PermissionDef(BaseModel):
    """A permission definition mapping tool/action to required autonomy."""
    tool_name: str
    required_level: AutonomyLevel
    description: str = ""
    requires_approval: bool = False
    approval_timeout_ms: int = 300_000
    auto_approve_from: Optional[AutonomyLevel] = None


class PermissionCheck(BaseModel):
    """Result of a permission check."""
    tool_name: str
    autonomy_level: AutonomyLevel
    agent_id: str = ""
    colony_id: str = ""
    granted: bool = False
    reason: str = ""
    requires_approval: bool = False


class ApprovalRequest(BaseModel):
    """Request for autonomy level escalation."""
    request_id: str = Field(default_factory=_uid)
    agent_id: str = ""
    colony_id: str = ""
    current_level: AutonomyLevel = AutonomyLevel.L0_READONLY
    requested_level: AutonomyLevel = AutonomyLevel.L2_MODERATE
    justification: str = ""
    task_context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now)
    expires_at: Optional[datetime] = None
    approved: Optional[bool] = None
    approver: Optional[str] = None
    auto_approved: bool = False


class EscalationRecord(BaseModel):
    """Record of a time-bounded autonomy escalation."""
    record_id: str = Field(default_factory=_uid)
    agent_id: str = ""
    colony_id: str = ""
    from_level: AutonomyLevel
    to_level: AutonomyLevel
    reason: str = ""
    granted_at: datetime = Field(default_factory=_now)
    expires_at: datetime
    auto_approved: bool = False
    approval_request_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# A2A TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class A2AMessage(BaseModel):
    """Agent-to-Agent protocol message."""
    version: str = "1.0"
    message_id: str = Field(default_factory=_uid)
    timestamp: datetime = Field(default_factory=_now)
    sender: Dict[str, str] = Field(default_factory=dict)  # agent_id, colony_id, hand_type
    recipient: Dict[str, str] = Field(default_factory=dict)  # agent_id, colony_id, or broadcast
    message_type: A2AMessageType = A2AMessageType.TASK_DELEGATION
    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)  # correlation_id, reply_to, etc.
    ttl: int = 300  # seconds


class A2AHandshake(BaseModel):
    """A2A handshake sequence state."""
    initiator_id: str
    responder_id: str
    state: str = "init"  # init → ack → complete
    initiator_capabilities: List[str] = Field(default_factory=list)
    responder_capabilities: List[str] = Field(default_factory=list)
    protocol_version: str = "1.0"
    started_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None


class A2ACapabilityAd(BaseModel):
    """Capability advertisement for A2A discovery."""
    agent_id: str
    colony_id: str
    hand_type: Optional[HandType] = None
    capabilities: List[str] = Field(default_factory=list)
    available: bool = True
    load: float = 0.0  # 0.0–1.0
    advertised_at: datetime = Field(default_factory=_now)
    ttl: int = 300


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class Event(BaseModel):
    """An event on the system-wide event bus."""
    event_id: str = Field(default_factory=_uid)
    event_type: EventType
    source: str = ""
    timestamp: datetime = Field(default_factory=_now)
    data: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# CHANNEL MESSAGE TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class InlineKeyboard(BaseModel):
    """Telegram-style inline keyboard button."""
    text: str
    callback_data: str = ""
    url: str = ""


class EmbedField(BaseModel):
    """Discord-style embed field."""
    name: str
    value: str
    inline: bool = False


class BlockElement(BaseModel):
    """Slack-style block kit element."""
    type: str = "section"
    text: str = ""
    fields: List[Dict[str, str]] = Field(default_factory=list)


class ChannelMessage(BaseModel):
    """Universal message type for channel communication."""
    message_id: str = Field(default_factory=_uid)
    channel_type: ChannelType
    channel_id: str = ""
    sender_id: str = ""
    recipient_id: str = ""
    text: str = ""
    format: MessageFormat = MessageFormat.MARKDOWN
    inline_keyboard: Optional[List[List[InlineKeyboard]]] = None
    embed_fields: Optional[List[EmbedField]] = None
    block_elements: Optional[List[BlockElement]] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None  # image, video, document
    template_name: Optional[str] = None
    template_params: Dict[str, str] = Field(default_factory=dict)
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None
    timestamp: datetime = Field(default_factory=_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChannelConfig(BaseModel):
    """Configuration for a communication channel."""
    channel_type: ChannelType
    enabled: bool = False
    token: str = ""
    api_url: str = ""
    webhook_url: str = ""
    allowed_chat_ids: List[str] = Field(default_factory=list)
    rate_limit_rpm: int = 30
    max_message_length: int = 4096
    extra: Dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# SKILL TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class SkillDef(BaseModel):
    """Definition of a reusable skill."""
    name: str
    version: str = "1.0.0"
    category: str = ""
    autonomy_level: AutonomyLevel = AutonomyLevel.L1_SAFE_OPS
    tools_required: List[str] = Field(default_factory=list)
    skills_required: List[str] = Field(default_factory=list)
    timeout_ms: int = 60_000
    tags: List[str] = Field(default_factory=list)
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# API REQUEST/RESPONSE TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class APIError(BaseModel):
    """Standard API error response."""
    code: str = "UNKNOWN"
    message: str = ""
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    has_next: bool = False
