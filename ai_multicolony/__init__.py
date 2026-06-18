"""AI-MultiColony: Colony-Based Autonomous Agent Operating System.

A multi-agent colony-based architecture with MCP tool integration,
Letta-style memory paging, graph-based orchestration, and
inter-colony communication.

Packages
--------
agents        – Agent types, registry, and lifecycle
colony        – Colony management, hands, scheduling, A2A
security      – Security analysis, audit trail, permissions
api           – FastAPI application, routes, schemas, WebSocket
channels      – Telegram, WhatsApp, Discord, Slack integrations
types         – All Pydantic v2 models and enums
config        – Settings and configuration
tools         – Built-in tool implementations
memory        – Multi-tier memory management
mcp           – Model Context Protocol server and client
browser       – Browser automation with stealth patterns
sources       – Intelligence sources (OSINT, economic, market)
harness       – Agent orchestration (graph, skills, sandbox, memory)
organism      – Self-evolution (sense, decision, factory, immune, growth)
finance       – Financial intelligence (risk guard, kill switch, regime)
integrations  – External framework adapters (CrewAI, AutoGen, LangGraph)
"""

__version__ = "0.2.0"

from .types import (
    # Enums
    AgentType,
    AgentState,
    AutonomyLevel,
    ColonyStatus,
    TaskStatus,
    TaskPriority,
    ToolCategory,
    MemoryTier,
    HandType,
    EventType,
    CondenserType,
    AuditLevel,
    AuditEventType,
    MessageFormat,
    A2AMessageType,
    ColonyScale,
    RoutingStrategy,
    CircuitBreakerState,
    ChannelType,
    # Agent types
    AgentSpec,
    AgentInfo,
    AgentCapabilities,
    # Colony types
    ColonyConfig,
    ColonyInfo,
    ColonyHealth,
    HandConfig,
    # Task types
    Task,
    TaskResult,
    TaskDeadline,
    # Tool types
    ToolCall,
    ToolResult,
    ToolSpec,
    # MCP message types
    MCPRequest,
    MCPResponse,
    MCPNotification,
    # Memory types
    MemoryPage,
    TemporalFact,
    TreeNode,
    FactQuery,
    # Security types
    AuditEntry,
    AuditEvent,
    AuditQuery,
    PermissionDef,
    PermissionCheck,
    ApprovalRequest,
    EscalationRecord,
    RoleDef,
    # A2A types
    A2AMessage,
    A2AHandshake,
    A2ACapabilityAd,
    # Event types
    Event,
    # Channel message types
    ChannelMessage,
    ChannelConfig,
    InlineKeyboard,
    EmbedField,
    BlockElement,
    # Skill types
    SkillDef,
    # API types
    APIError,
    PaginatedResponse,
)

from .agents import (
    BaseAgent,
    EventBus,
    CircuitBreaker,
    ManusAgent,
    PlannerAgent,
    ExecutorAgent,
    CoderAgent,
    BrowserAgent,
    VoiceAgent,
    SecurityAgent,
    ResearcherAgent,
    ColonyAgent,
    AgentRegistry,
    SharedAgentState,
)

from .tools import (
    ShellTool,
    FileTool,
    BrowserTool,
    SearchTool,
    CodeTool,
    MCPToolBase,
    DockerTool,
    VoiceTool,
    MemoryTool,
    ChannelTool,
)

from .mcp import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    MCPServer,
    RateLimiter,
    MCPClient,
    PermissionEngine as MCPPermissionEngine,
)

from .memory import (
    MemoryManager,
    VectorStore,
    PagingManager,
    KnowledgeBase,
    SummaryCondenser,
    ExtractionCondenser,
    TemporalCondenser,
    RollupCondenser,
    DeduplicationCondenser,
    PriorityCondenser,
    SlidingWindowCondenser,
    HierarchicalCondenser,
)

from .colony import (
    Colony,
    ColonyManager,
    SCALE_PRESETS,
    Hand,
    HandManager,
    SecurityHand,
    CodeHand,
    ResearchHand,
    BrowserHand,
    VoiceHand,
    ComputeHand,
    IntegrationHand,
    HAND_DESCRIPTIONS,
    HAND_DEFAULTS,
    TaskScheduler,
    A2ACoordinator,
)

from .browser import StealthPatterns, StealthConfig, HumanBehavior

from .security import (
    SecurityAnalyzer,
    SecurityFinding,
    AuditTrail,
    PermissionEngine,
)

from .channels import (
    TelegramBot,
    WhatsAppGateway,
    DiscordBot,
    SlackIntegration,
)

from .api import (
    FastAPIApp,
    create_app,
    AuthMiddleware,
    RateLimitMiddleware,
)

from .config import Settings, get_settings

from .services import (
    get_agent_registry,
    get_tool_registry,
    get_mcp_server,
    get_memory_manager,
    get_colony_manager,
    get_security_analyzer,
    get_audit_logger,
    reset_services,
)

from .worker import AsyncWorker

from .exceptions import (
    MultiColonyError,
    AgentError,
    AgentNotFoundError,
    AgentTimeoutError,
    AgentStateError,
    ColonyError,
    ColonyNotFoundError,
    ColonyFullError,
    ToolError,
    ToolNotFoundError,
    ToolPermissionError,
    MemoryError,
    MemoryCompactionError,
    MCPError,
    MCPProtocolError,
    SecurityError,
    PermissionDeniedError,
)

__all__ = [
    "__version__",
    # Types - Enums
    "AgentType",
    "AgentState",
    "AutonomyLevel",
    "ColonyStatus",
    "TaskStatus",
    "TaskPriority",
    "ToolCategory",
    "MemoryTier",
    "HandType",
    "EventType",
    "CondenserType",
    "AuditLevel",
    "AuditEventType",
    "MessageFormat",
    "A2AMessageType",
    "ColonyScale",
    "RoutingStrategy",
    "CircuitBreakerState",
    "ChannelType",
    # Types - Models
    "AgentSpec",
    "AgentInfo",
    "AgentCapabilities",
    "ColonyConfig",
    "ColonyInfo",
    "ColonyHealth",
    "HandConfig",
    "Task",
    "TaskResult",
    "TaskDeadline",
    "ToolCall",
    "ToolResult",
    "ToolSpec",
    "MCPRequest",
    "MCPResponse",
    "MCPNotification",
    "MemoryPage",
    "TemporalFact",
    "TreeNode",
    "FactQuery",
    "AuditEntry",
    "AuditEvent",
    "AuditQuery",
    "PermissionDef",
    "PermissionCheck",
    "ApprovalRequest",
    "EscalationRecord",
    "RoleDef",
    "A2AMessage",
    "A2AHandshake",
    "A2ACapabilityAd",
    "Event",
    "ChannelMessage",
    "ChannelConfig",
    "InlineKeyboard",
    "EmbedField",
    "BlockElement",
    "SkillDef",
    "APIError",
    "PaginatedResponse",
    # Agents
    "BaseAgent",
    "EventBus",
    "CircuitBreaker",
    "ManusAgent",
    "PlannerAgent",
    "ExecutorAgent",
    "CoderAgent",
    "BrowserAgent",
    "VoiceAgent",
    "SecurityAgent",
    "ResearcherAgent",
    "ColonyAgent",
    "AgentRegistry",
    "SharedAgentState",
    # Tools
    "ShellTool",
    "FileTool",
    "BrowserTool",
    "SearchTool",
    "CodeTool",
    "MCPToolBase",
    "DockerTool",
    "VoiceTool",
    "MemoryTool",
    "ChannelTool",
    # MCP
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCError",
    "MCPServer",
    "RateLimiter",
    "MCPClient",
    "MCPPermissionEngine",
    # Memory
    "MemoryManager",
    "VectorStore",
    "PagingManager",
    "KnowledgeBase",
    "SummaryCondenser",
    "ExtractionCondenser",
    "TemporalCondenser",
    "RollupCondenser",
    "DeduplicationCondenser",
    "PriorityCondenser",
    "SlidingWindowCondenser",
    "HierarchicalCondenser",
    # Colony
    "Colony",
    "ColonyManager",
    "SCALE_PRESETS",
    "Hand",
    "HandManager",
    "SecurityHand",
    "CodeHand",
    "ResearchHand",
    "BrowserHand",
    "VoiceHand",
    "ComputeHand",
    "IntegrationHand",
    "HAND_DESCRIPTIONS",
    "HAND_DEFAULTS",
    "TaskScheduler",
    "A2ACoordinator",
    # Browser
    "StealthPatterns",
    "StealthConfig",
    "HumanBehavior",
    # Security
    "SecurityAnalyzer",
    "SecurityFinding",
    "AuditTrail",
    "PermissionEngine",
    # Channels
    "TelegramBot",
    "WhatsAppGateway",
    "DiscordBot",
    "SlackIntegration",
    # API
    "FastAPIApp",
    "create_app",
    "AuthMiddleware",
    "RateLimitMiddleware",
    # Config
    "Settings",
    "get_settings",
    # Services
    "get_agent_registry",
    "get_tool_registry",
    "get_mcp_server",
    "get_memory_manager",
    "get_colony_manager",
    "get_security_analyzer",
    "get_audit_logger",
    "reset_services",
    # Worker
    "AsyncWorker",
    # Exceptions
    "MultiColonyError",
    "AgentError",
    "AgentNotFoundError",
    "AgentTimeoutError",
    "AgentStateError",
    "ColonyError",
    "ColonyNotFoundError",
    "ColonyFullError",
    "ToolError",
    "ToolNotFoundError",
    "ToolPermissionError",
    "MemoryError",
    "MemoryCompactionError",
    "MCPError",
    "MCPProtocolError",
    "SecurityError",
    "PermissionDeniedError",
]

# ── New subpackages (v0.2.0) ────────────────────────────────────────────────

from .sources import (
    SourceProvider,
    SourceCategory,
    SourceConfig,
    SourceItem,
    SourceReliability,
    SourceResult,
    SourceStatus,
    OSINTSource,
    EconomicSource,
    MarketSource,
    SourceManager,
)

from .harness import (
    HarnessGraph,
    SkillRegistry,
    SkillDefinition,
    SandboxManager,
    SandboxConfig,
    HarnessMemory,
)

from .organism import (
    SenseEngine,
    DecisionEngine,
    SolutionFactory,
    ImmuneSystem,
    GrowthEngine,
    LifecycleOrchestrator,
)

from .finance import (
    ConstitutionalRiskGuard,
    KillSwitch,
    MarketRegimeDetector,
    PressureEngine,
    AutoSwitcher,
)

from .integrations import (
    CrewAIAdapter,
    AutoGenAdapter,
    LangGraphAdapter,
)

__all__.extend([
    # Sources
    "SourceProvider",
    "SourceCategory",
    "SourceConfig",
    "SourceItem",
    "SourceReliability",
    "SourceResult",
    "SourceStatus",
    "OSINTSource",
    "EconomicSource",
    "MarketSource",
    "SourceManager",
    # Harness
    "HarnessGraph",
    "SkillRegistry",
    "SkillDefinition",
    "SandboxManager",
    "SandboxConfig",
    "HarnessMemory",
    # Organism
    "SenseEngine",
    "DecisionEngine",
    "SolutionFactory",
    "ImmuneSystem",
    "GrowthEngine",
    "LifecycleOrchestrator",
    # Finance
    "ConstitutionalRiskGuard",
    "KillSwitch",
    "MarketRegimeDetector",
    "PressureEngine",
    "AutoSwitcher",
    # Integrations
    "CrewAIAdapter",
    "AutoGenAdapter",
    "LangGraphAdapter",
])
